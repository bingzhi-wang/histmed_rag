# scripts/index_corpus.py
import json
import uuid
from pathlib import Path

from tqdm import tqdm
from FlagEmbedding import BGEM3FlagModel
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

COLLECTION       = 'histmed_corpus'
EMBED_BATCH_SIZE = 32    # Chunks per embedding batch — lower if OOM
UPSERT_BATCH_SIZE = 200  # Points per Qdrant upsert call
VECTOR_DIM       = 1024  # BGE-M3 dense vector dimension
MODEL_PATH       = 'BAAI/bge-m3'  # Or local path e.g. 'models/embeddings/bge-m3'
PROCESSED        = Path('corpus/processed')
RECREATE = True          # chunk_ids + embedding strategy changed → rebuild clean

# Helper
def embedding_text(chunk: dict) -> str:
    '''Embed translation + original so English queries match a non-English corpus.'''
    orig  = (chunk.get('text') or '').strip()
    trans = (chunk.get('text_translation') or '').strip()
    return f'{trans}\n\n{orig}' if trans else orig

# Stable custom namespace so chunk_id → UUID is deterministic and collision-free
_NS = uuid.uuid5(uuid.NAMESPACE_URL, 'histmed_corpus/chunk_id')

# ---------------------------------------------------------------------------
# Model + client setup
# ---------------------------------------------------------------------------
print('Loading BGE-M3 embedding model...')
embed_model = BGEM3FlagModel(MODEL_PATH, use_fp16=True)
print('Model loaded.')

client = QdrantClient(host='localhost', port=6333)


def ensure_collection():
    """Create the Qdrant collection if it doesn't already exist."""
    """enhanced with a recreate-aware version"""
    existing = {c.name for c in client.get_collections().collections}
    if RECREATE and COLLECTION in existing:
        client.delete_collection(COLLECTION)
        existing.discard(COLLECTION)
        print(f"Collection '{COLLECTION}' dropped for clean rebuild.")
    if COLLECTION not in existing:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE))
        print(f"Collection '{COLLECTION}' created.")

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_all_chunks() -> list[dict]:
    chunks = []
    for jsonl_file in PROCESSED.glob('*.jsonl'):
        with open(jsonl_file, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                chunk = json.loads(line)
                if chunk.get('text', '').strip():
                    chunks.append(chunk)
    print(f'Total chunks loaded: {len(chunks)}')
    return chunks


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------
def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts with BGE-M3's dense encoder."""
    result = embed_model.encode(
        texts,
        batch_size=len(texts),   # list is already sliced to EMBED_BATCH_SIZE
        max_length=2048,
        return_dense=True,
        return_sparse=False,     # sparse handled separately in ES
        return_colbert_vecs=False,
    )
    return result['dense_vecs'].tolist()


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------
def index_all():
    ensure_collection()
    chunks = load_all_chunks()
    pending: list[PointStruct] = []

    for i in tqdm(range(0, len(chunks), EMBED_BATCH_SIZE), desc='Embedding & indexing'):
        batch = chunks[i : i + EMBED_BATCH_SIZE]
        texts = [embedding_text(c) for c in batch]   # was [c['text'] for c in batch
        vectors = embed_batch(texts)

        for chunk, vector in zip(batch, vectors):
            payload = dict(chunk)           # copy all fields including 'text'
            point = PointStruct(
                id=str(uuid.uuid5(_NS, chunk['chunk_id'])),
                vector=vector,
                payload=payload,
            )
            pending.append(point)

        if len(pending) >= UPSERT_BATCH_SIZE:
            client.upsert(collection_name=COLLECTION, points=pending)
            pending.clear()

    # Flush remainder
    if pending:
        client.upsert(collection_name=COLLECTION, points=pending)

    count = client.count(COLLECTION).count
    print(f'Indexing complete. Qdrant collection "{COLLECTION}" now has {count} vectors.')


if __name__ == '__main__':
    index_all()
