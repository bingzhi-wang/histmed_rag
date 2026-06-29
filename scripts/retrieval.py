# scripts/retrieval.py
import torch
from FlagEmbedding import BGEM3FlagModel, FlagReranker
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny, Range
from elasticsearch import Elasticsearch
from dataclasses import dataclass
from typing import Optional

COLLECTION = 'histmed_corpus'

@dataclass
class RetrievedChunk:
    chunk_id:         str
    text:             str
    source_text:      str
    language:         str
    tradition:        str
    section:          str
    date_label:       str
    score:            float
    text_translation: str = ''            # English (rerank/synthesis basis)
    source_urn:       str = ''            # NEW — provenance (B1/B3/B4)
    section_ref:      str = ''            # NEW — locator fallback (B4)
    date_approx:      Optional[int] = None  # NEW — numeric date (B3)
    chapter_ref:      str = ''            # NEW — Suwen/Causae locator (B4)

def _rerank_text(payload: dict) -> str:
    '''Prefer the English translation for cross-encoder scoring.'''
    return (payload.get('text_translation') or payload.get('text') or '').strip()

class HybridRetriever:
    def __init__(self):
        print('Initializing retrieval components...')
        self.embed_model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)
        self.reranker = FlagReranker('BAAI/bge-reranker-v2-m3', use_fp16=True)
        self.qdrant = QdrantClient(host='localhost', port=6333)
        self.es = Elasticsearch('http://localhost:9200')
        print('Retriever ready.')

    def _embed_query(self, query: str) -> list:
        result = self.embed_model.encode(
            [query], return_dense=True,
            return_sparse=False, return_colbert_vecs=False)
        return result['dense_vecs'][0].tolist()

    def _qdrant_search(self, query_vec, top_k=30,
                        filter_languages=None, filter_traditions=None,
                        date_from=None, date_to=None):
        conditions = []
        if filter_languages:
            conditions.append(FieldCondition(
                key='language', match=MatchAny(any=filter_languages)))
        if filter_traditions:
            conditions.append(FieldCondition(
                key='tradition', match=MatchAny(any=filter_traditions)))
        if date_from is not None or date_to is not None:
            conditions.append(FieldCondition(
                key='date_approx', range=Range(gte=date_from, lte=date_to)))
        qdrant_filter = Filter(must=conditions) if conditions else None
        results = self.qdrant.search(
            collection_name=COLLECTION, query_vector=query_vec,
            limit=top_k, query_filter=qdrant_filter, with_payload=True)
        return {hit.payload['chunk_id']: (i + 1, hit.payload)
                for i, hit in enumerate(results)}

    def _es_search(self, query: str, top_k=30):
        '''BM25 over translation + original. Translation carries English queries.'''
        body = {
            'query': {'multi_match': {
                'query': query,
                'fields': ['text_translation^2', 'text', 'section'],  # CHANGED
                'type': 'best_fields',
            }},
            'size': top_k,
        }
        resp = self.es.search(index='histmed_corpus', body=body)
        return {hit['_source']['chunk_id']: (i + 1, hit['_source'])
                for i, hit in enumerate(resp['hits']['hits'])}

    def _rrf(self, *rankings, k=60):
        scores, payloads = {}, {}
        for ranking in rankings:
            for chunk_id, (rank, payload) in ranking.items():
                scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
                payloads.setdefault(chunk_id, payload)   # CHANGED: keep richer (Qdrant) payload
        merged = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [(cid, payloads[cid]) for cid, _ in merged]

    def _rerank(self, query: str, candidates: list):
        '''Cross-encoder rerank. candidates: list of (chunk_id, payload).
        Returns ALL as RetrievedChunk sorted by score desc (no truncation).'''
        if not candidates:
            return []
        pairs  = [[query, _rerank_text(p)] for _, p in candidates]
        scores = self.reranker.compute_score(pairs, normalize=True)
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        return [
            RetrievedChunk(
                chunk_id=p['chunk_id'], text=p.get('text', ''),
                text_translation=p.get('text_translation', ''),
                source_text=p.get('source_text', ''),
                language=p.get('language', ''),
                tradition=p.get('tradition', ''),
                section=p.get('section', ''),
                date_label=p.get('date_label', ''),
                source_urn=p.get('source_urn', ''),
                section_ref=p.get('section_ref', ''),
                date_approx=p.get('date_approx'),
                chapter_ref=p.get('chapter_ref', ''),
                score=score)
            for (_, p), score in ranked
        ]

    def _select(self, ranked, top_k, floor_traditions, min_per_tradition, per_source_cap):
        '''Diversify: collapse near-duplicates, guarantee a per-tradition floor,
        cap per source, fill by score to top_k. Final order = relevance.'''
        seen, deduped = set(), []
        for c in ranked:                      # collapse same section / shared translation
            key = (c.tradition,
                (c.chapter_ref or c.section_ref or c.section or '').strip(),
                (c.text_translation or c.text or '').strip()[:120])
            if key in seen:
                continue
            seen.add(key); deduped.append(c)

        selected, used, src_count = [], set(), {}
        def take(i, c):
            selected.append(c); used.add(i)
            src_count[c.source_text] = src_count.get(c.source_text, 0) + 1

        for trad in floor_traditions:         # floor: guarantee each tradition
            taken = 0
            for i, c in enumerate(deduped):
                if len(selected) >= top_k or taken >= min_per_tradition:
                    break
                if i in used or c.tradition != trad:
                    continue
                if src_count.get(c.source_text, 0) >= per_source_cap:
                    continue
                take(i, c); taken += 1

        for i, c in enumerate(deduped):       # fill by score, respect source cap
            if len(selected) >= top_k:
                break
            if i in used or src_count.get(c.source_text, 0) >= per_source_cap:
                continue
            take(i, c)

        for i, c in enumerate(deduped):       # relax cap only if still short
            if len(selected) >= top_k:
                break
            if i not in used:
                take(i, c)

        selected.sort(key=lambda c: c.score, reverse=True)   # preserves [SOURCE N] invariant
        return selected[:top_k]

    def retrieve(self, query: str, top_k=10,
                filter_languages=None, filter_traditions=None,
                date_from=None, date_to=None,
                floor_traditions=None, min_per_tradition=0,
                per_source_cap=3, rerank_pool=50):
        query_vec = self._embed_query(query)
        dense  = self._qdrant_search(query_vec, 60, filter_languages,
                                    filter_traditions, date_from, date_to)
        sparse = self._es_search(query, 60)
        fused  = self._rrf(dense, sparse)                 # [(cid, payload)] by RRF

        pool     = fused[:rerank_pool]
        pool_ids = {cid for cid, _ in pool}

        # guarantee each floor tradition has candidates in the rerank pool,
        # even if it ranked outside the global top pool (reuses query_vec)
        if floor_traditions and min_per_tradition > 0:
            for trad in floor_traditions:
                hits = self._qdrant_search(query_vec, max(min_per_tradition * 4, 8),
                                        filter_languages, [trad], date_from, date_to)
                for cid, (_, p) in hits.items():
                    if cid not in pool_ids:
                        pool.append((cid, p)); pool_ids.add(cid)

        ranked = self._rerank(query, pool)
        return self._select(ranked, top_k, floor_traditions or [],
                            min_per_tradition, per_source_cap)
