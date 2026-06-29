# Architecture & Technical Reference

Internals of the Historical Medical RAG system. The [README](README.md) covers what it does; this covers how, plus install detail, verification, and troubleshooting.

## Pipeline

A compiled **LangGraph** state machine of five single-responsibility agents. Retrieval and synthesis operate on **English translations** of every passage, which is what makes cross-lingual search work: an English query reliably finds the relevant Chinese or Latin chunk.

```
USER QUERY
   │
   ▼  1. QUERY ANALYSIS    expand terms across traditions; emit tradition/language/date filters
   ▼  2. RETRIEVAL         dense (Qdrant+BGE-M3) + BM25 (Elasticsearch) → RRF fusion
   │                       → cross-encoder rerank → per-tradition diversification
   ▼  3. SYNTHESIS         grounded comparative answer; cite every claim with [SOURCE N]
   ▼  4. PROOFREADING      structural check (no LLM) + per-claim verification (LLM judge)
   │                          └─ recall gap? → back to RETRIEVAL (max 2 passes)
   ▼  5. CITATION          academic references from metadata + original & translation
   ▼
Console answer · JSONL trace · Markdown export
```

**The agents**

1. **Query Analysis** — rewrites the query with cross-tradition equivalent terms; emits retrieval filters (traditions, languages, optional date range).
2. **Retrieval** — hybrid dense + sparse search fused by Reciprocal Rank Fusion, reranked by a cross-encoder, then *diversified*: near-duplicate passages collapsed, each requested tradition guaranteed a minimum number of slots (per-tradition floor), no single work allowed to dominate (per-source cap).
3. **Synthesis** — grounded comparative analysis using only retrieved passages, each claim tagged `[SOURCE N]`, refusing to fill gaps from outside knowledge.
4. **Proofreading** — a deterministic structural check (does every `[SOURCE N]` resolve to a real chunk?) plus an LLM judge verifying each claim against the translation it cites; flags unsupported claims, misattribution, anachronism, over-translation. A genuine recall gap routes back to Retrieval, capped at two passes.
5. **Citation** — per-tradition academic references from metadata, embedding the original text and English translation of every cited passage.

## Provenance & traceability

Every `[SOURCE N]` in the prose resolves to a concrete `chunk_id`, `source_urn` (Perseus CTS where available), section, and tradition. Two verification layers: a deterministic integrity check (no citation may point at a non-existent source) and an LLM judge (the cited passage must actually support the claim). Each run persists two timestamped artifacts:

- `logs/<date>_<slug>_<id>.jsonl` — one JSON record per run: query, expanded terms, every retrieved chunk with rerank score, the draft, final answer, resolved citations (with full original + translation), and per-claim verifications.
- `exports/<date>_<slug>_<id>.md` — a clean, shareable answer stamped with the date of input.

```bash
# read the latest trace, cited sources only
python3 -c "import json,glob,os; f=max(glob.glob('logs/*.jsonl'),key=os.path.getmtime); r=json.loads(open(f).read()); print(f); print('cited:', r['cited_source_ns'])"
```

## Components

| Layer | Tool | Role |
|-------|------|------|
| Embeddings | BGE-M3 (1024-dim) | Multilingual dense vectors; each chunk embedded as *translation + original* |
| Vector store | Qdrant | Cosine ANN search; metadata filters on tradition/language/date; deterministic `uuid5` point IDs |
| Keyword store | Elasticsearch | BM25 (k1=1.5, b=0.75) over translation (boosted), original, section |
| Rerank | BGE-reranker-v2-m3 | Cross-encoder rescoring of the fused pool against English text |
| Generation | Ollama + qwen3:14b | Local; `num_ctx=16384`, strips `<think>`, JSON mode for structured agents; CPU-only, offloads to GPU when present |
| Orchestration | LangGraph | Typed `AgentState`; conditional re-retrieval capped at two passes |

## Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4-core | 8-core |
| RAM | 16 GB | 32 GB |
| GPU (optional) | — | NVIDIA 12 GB+ VRAM (offloads qwen3:14b) |
| Storage | 50 GB | 50 GB |
| OS / Python | Ubuntu 20.04+, Python 3.10/3.11 | Ubuntu 22.04, Python 3.11 |

Designed to run **CPU-only and fully offline**; a GPU only speeds up inference.

## Full install

```bash
# 1. System deps
sudo apt update && sudo apt install -y build-essential git curl wget \
  python3.11 python3.11-venv python3-pip default-jdk docker.io docker-compose-plugin

# 2. Project
cd ~/histmed_rag && python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Source texts (internet, once)
python scripts/download_suwen.py
#   place Hippocrates (Perseus) and Causae (OCR'd Latin) sources under corpus/raw/

# 4. Models (internet, once)
python3 -c "from FlagEmbedding import BGEM3FlagModel; BGEM3FlagModel('BAAI/bge-m3')"
python3 -c "from FlagEmbedding import FlagReranker; FlagReranker('BAAI/bge-reranker-v2-m3')"
ollama pull qwen3:14b

# 5. Preprocess → 6. Translate → 7. Infra → 8. Index   (ORDER MATTERS)
python scripts/preprocess_suwen.py
python scripts/preprocess_hippocrates.py
python scripts/preprocess_causae_txt.py
python scripts/translate_chunks.py          # retrieval ranks on the translation; must precede indexing
docker compose -f docker/docker-compose.yml up -d
ollama serve &
python scripts/setup_qdrant.py
python scripts/index_corpus.py
python scripts/index_elasticsearch.py
```

`start.sh` brings the stack up (Qdrant 6333, Elasticsearch 9200, Ollama 11434), waits for each, ensures the model is pulled, and launches `main.py`.

## Verify the index

All three counts should agree (≈ 1,224 chunks):

```bash
cat corpus/processed/*.jsonl | grep -c .                                            # source of truth
python3 -c "from qdrant_client import QdrantClient; print(QdrantClient(host='localhost',port=6333).count('histmed_corpus').count)"
curl -s localhost:9200/histmed_corpus/_count
```

If the JSONL count exceeds either index, re-run `index_corpus.py` then `index_elasticsearch.py` (translate first if translations changed).

## Test suite

`scripts/run_test_suite.py` runs 16 probe questions in one process (models load once), capturing each run's trace + export and writing `test_runs/<timestamp>/summary.{md,tsv}`.

```bash
./run_test_suite.sh --list      # preview
./run_test_suite.sh             # full battery
./run_test_suite.sh 7 8 12      # subset by number
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Connection refused (6333/9200) | Services still starting; `start.sh` waits, or pause after `docker compose up -d` |
| Out of memory | Lower `EMBED_BATCH_SIZE` in `index_corpus.py`; run qwen3:14b CPU-only |
| Docker won't start | `sudo systemctl start docker`; confirm user in `docker` group |
| Ollama not responding | `ollama serve &`; `ollama list` to confirm `qwen3:14b` |
| A tradition missing | Expected behaviour is the floor; check the latest trace's retrieved traditions |
| Index counts disagree | Re-index (translate first if translations changed) |
| `Permission denied` on `*.sh` | `chmod +x start.sh run_test_suite.sh` |

## Project structure

```
agents/        state.py · nodes.py · graph.py · trace_logger.py · answer_exporter.py
scripts/       download/preprocess/translate · index_corpus · index_elasticsearch · retrieval · run_test_suite
corpus/        raw/ · processed/{suwen,hippocrates,causaecurae}_chunks.jsonl
docker/        docker-compose.yml (Qdrant + Elasticsearch)
logs/ exports/ test_runs/    per-run traces, answers, suite results
main.py · start.sh · requirements.txt
```

## Known limitations

- **Temporal filtering** does not reliably convert phrases like "after 1000 CE" into a date filter; date-scoped queries may still return all traditions.
- **Single-tradition isolation** can leak, because the BM25 path is not tradition-filtered the way the dense path is.
- **Machine translation:** Chinese and Latin English are LLM-translated (Greek uses Perseus); every citation marks this. Verify quotations against the original.
