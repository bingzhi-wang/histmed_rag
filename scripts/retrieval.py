# scripts/retrieval.py
import torch
from FlagEmbedding import BGEM3FlagModel, FlagReranker
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny, Range
from elasticsearch import Elasticsearch
from dataclasses import dataclass, field
from typing import Optional

COLLECTION = 'histmed_corpus'

@dataclass
class RetrievedChunk:
    chunk_id:    str
    text:        str
    source_text: str
    language:    str
    tradition:   str
    section:     str
    date_label:  str
    score:       float

class HybridRetriever:
    def __init__(self):
        print('Initializing retrieval components...')
        self.embed_model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)
        self.reranker = FlagReranker(
            'BAAI/bge-reranker-v2-m3', use_fp16=True
        )
        self.qdrant = QdrantClient(host='localhost', port=6333)
        self.es = Elasticsearch('http://localhost:9200')
        print('Retriever ready.')

    def _embed_query(self, query: str) -> list:
        result = self.embed_model.encode(
            [query], return_dense=True,
            return_sparse=False, return_colbert_vecs=False
        )
        return result['dense_vecs'][0].tolist()

    def _qdrant_search(self, query_vec, top_k=30,
                        filter_languages=None, filter_traditions=None,
                        date_from=None, date_to=None):
        '''Dense vector search in Qdrant with optional metadata filters.'''
        qdrant_filter = None
        conditions = []
        if filter_languages:
            conditions.append(FieldCondition(
                key='language', match=MatchAny(any=filter_languages)))
        if filter_traditions:
            conditions.append(FieldCondition(
                key='tradition', match=MatchAny(any=filter_traditions)))
        if date_from is not None or date_to is not None:
            conditions.append(FieldCondition(
                key='date_approx',
                range=Range(gte=date_from, lte=date_to)))
        if conditions:
            qdrant_filter = Filter(must=conditions)
        results = self.qdrant.search(
            collection_name=COLLECTION,
            query_vector=query_vec,
            limit=top_k,
            query_filter=qdrant_filter,
            with_payload=True
        )
        return {hit.payload['chunk_id']: (i+1, hit.payload)
                for i, hit in enumerate(results)}

    def _es_search(self, query: str, top_k=30):
        '''BM25 keyword search in Elasticsearch.'''
        body = {
            'query': {'multi_match': {
                'query': query,
                'fields': ['text^2', 'section'],
                'type': 'best_fields'
            }},
            'size': top_k
        }
        resp = self.es.search(index='histmed_corpus', body=body)
        return {hit['_source']['chunk_id']: (i+1, hit['_source'])
                for i, hit in enumerate(resp['hits']['hits'])}

    def _rrf(self, *rankings, k=60):
        '''Reciprocal Rank Fusion: merge multiple ranked lists.'''
        scores = {}
        payloads = {}
        for ranking in rankings:
            for chunk_id, (rank, payload) in ranking.items():
                scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
                payloads[chunk_id] = payload
        merged = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [(cid, payloads[cid]) for cid, _ in merged]

    def _rerank(self, query: str, candidates: list, top_n=10):
        '''Cross-encoder reranking of top candidates.'''
        if not candidates: return []
        pairs = [[query, p['text']] for _, p in candidates[:20]]
        scores = self.reranker.compute_score(pairs, normalize=True)
        ranked = sorted(zip(candidates[:20], scores),
                         key=lambda x: x[1], reverse=True)
        return [
            RetrievedChunk(
                chunk_id=p['chunk_id'], text=p['text'],
                source_text=p.get('source_text',''),
                language=p.get('language',''),
                tradition=p.get('tradition',''),
                section=p.get('section',''),
                date_label=p.get('date_label',''),
                score=score
            )
            for (_, p), score in ranked[:top_n]
        ]

    def retrieve(self, query: str, top_k=10,
                 filter_languages=None, filter_traditions=None,
                 date_from=None, date_to=None):
        '''Full hybrid retrieval pipeline: dense + BM25 + RRF + reranking.'''
        query_vec = self._embed_query(query)
        dense_results = self._qdrant_search(
            query_vec, 30, filter_languages, filter_traditions,
            date_from, date_to)
        sparse_results = self._es_search(query, 30)
        fused = self._rrf(dense_results, sparse_results)
        return self._rerank(query, fused, top_k)
