# config/settings.py
# ── Edit these values to customize your system ──────────────────────

# LLM (Ollama model name — must match what you pulled with 'ollama pull')
MODEL_NAME = 'qwen3:14b'

# Embedding model
EMBED_MODEL = 'BAAI/bge-m3'  # Or local path: 'models/embeddings/bge-m3'

# Reranker model
RERANKER_MODEL = 'BAAI/bge-reranker-v2-m3'

# Vector store
QDRANT_HOST       = 'localhost'
QDRANT_PORT       = 6333
QDRANT_COLLECTION = 'histmed_corpus'

# Elasticsearch
ES_HOST  = 'http://localhost:9200'
ES_INDEX = 'histmed_corpus'

# Retrieval parameters
DENSE_TOP_K    = 30  # Initial dense retrieval candidates
SPARSE_TOP_K   = 30  # Initial BM25 candidates
RERANK_TOP_N   = 10  # Final results after reranking

# Chunking parameters
SUWEN_CHUNK_CHARS    = 400
GREEK_CHUNK_CHARS    = 500
LATIN_CHUNK_CHARS    = 450

# Agent parameters
MAX_RETRIEVAL_ITERATIONS = 2  # Max re-retrieval loops
