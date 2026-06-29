# Historical Medical RAG System
## Cross-Cultural Analysis of Ancient Medical Texts

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-required-2496ED.svg)](https://www.docker.com/)
[![Ollama](https://img.shields.io/badge/ollama-qwen3%3A14b-000000.svg)](https://ollama.ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A **fully offline, agentic** Retrieval-Augmented Generation system for comparative history of medicine. It lets three physicians — one Chinese, one Greek, one Medieval Latin, writing across roughly **1,500 years and three languages** — answer the same research question side by side, and it shows you exactly which passage every claim came from. No internet, no API keys, no cloud.

---

## 📋 Table of Contents
- [Why this exists](#why-this-exists)
- [The Three Traditions](#the-three-traditions)
- [How It Works](#how-it-works)
- [What Makes It Different: Traceable Provenance](#what-makes-it-different-traceable-provenance)
- [Example Run & Results](#example-run--results)
- [Hardware Requirements](#hardware-requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Outputs: Traces & Answer Exports](#outputs-traces--answer-exports)
- [Verify the Index](#verify-the-index)
- [Project Structure](#project-structure)
- [Technical Notes](#technical-notes)
- [Troubleshooting](#troubleshooting)
- [Citing the System](#citing-the-system)
- [License](#license)

---

## Why this exists

Comparative medical history is hard for an ordinary RAG system: the sources are in **Classical Chinese, Ancient Greek, and Medieval Latin**, the concepts don't map cleanly onto each other (*qì* is not *pneuma* is not *humores*), and a scholar needs to **trust every citation**. This system was built to solve exactly that — cross-lingual retrieval that actually surfaces the right tradition, grounded synthesis that refuses to invent, and a provenance trail you can audit line by line.

- 🔒 **Complete privacy** — nothing leaves your machine.
- 💰 **Zero API cost** — every model runs locally.
- 🌐 **Offline after setup** — internet needed only to download texts and models once.
- 🧠 **Agentic** — five LangGraph agents plan, retrieve, synthesize, verify, and cite.
- 🔍 **Traceable** — every `[SOURCE N]` resolves to a real chunk, with original + translation, persisted per run.

---

## The Three Traditions

| Text | Language / Period | Translation | Focus |
|------|-------------------|-------------|-------|
| **黄帝内经素問** *(Huángdì Nèijīng Sùwèn)* | Classical Chinese · ~300–100 BCE | LLM-translated → English | Qì, yin-yang, the five phases (wǔ xíng), organ–season correspondence, preventive seasonal medicine |
| **Hippocrates — *On Ancient Medicine* & *Prognostic*** | Ancient Greek · ~420–350 BCE | Perseus parallel English | Humoral balance, heat/cold as pathogenic forces, the art of medicine, clinical prognosis |
| **Causae et Curae** *(Hildegard von Bingen)* | Medieval Latin (OCR'd) · ~1150–1160 CE | LLM-translated → English | Humoral-cosmological disease, the four temperaments, bile and melancholy, remedies |

> **Provenance note.** The Greek corpus comprises two Hippocratic works — *On Ancient Medicine* (`tlg0627.tlg001`) and *Prognostic* (`tlg0627.tlg003`) — taken from the Perseus Digital Library. An earlier file labelled *Peri Nouson / De Morbis* was found to actually contain the *Epidemics* and was removed. Greek English is used directly from Perseus; the Chinese and Latin English are machine translations and are marked as such in every citation.

---

## How It Works

The pipeline is a compiled **LangGraph** state machine of five single-responsibility agents. Retrieval and synthesis operate on **English translations** of every passage, which is what makes cross-lingual search work: an English query reliably finds the relevant Chinese or Latin chunk.

```
                          USER QUERY
                              │
                ┌─────────────▼─────────────┐
                │   1. QUERY ANALYSIS       │  expand terms across traditions;
                │      (JSON-mode LLM)      │  emit tradition/language/date filters
                └─────────────┬─────────────┘
                ┌─────────────▼─────────────┐
                │   2. RETRIEVAL            │  Dense (Qdrant + BGE-M3)
                │                           │  + BM25 (Elasticsearch)
                │                           │  → RRF fusion → cross-encoder rerank
                │                           │  → per-tradition diversification
                └─────────────┬─────────────┘
                ┌─────────────▼─────────────┐
                │   3. SYNTHESIS            │  grounded comparative analysis;
                │      (qwen3:14b)          │  cite every claim with [SOURCE N]
                └─────────────┬─────────────┘
                ┌─────────────▼─────────────┐
                │   4. PROOFREADING         │  structural check (no LLM) +
                │                           │  per-claim verification (LLM judge)
                └─────────────┬─────────────┘
                     needs more sources?
                       │            │
                   yes │            │ no
          ┌────────────┘            └────────────┐
          ▼ (back to Retrieval, max 2x)          ▼
                                ┌─────────────────────────┐
                                │   5. CITATION           │  academic citations from
                                │                         │  metadata + original &
                                │                         │  translation per source
                                └────────────┬────────────┘
                                             ▼
                            Console answer · JSONL trace · Markdown export
```

**The agents**

1. **Query Analysis** — rewrites the query with cross-tradition equivalent terms and emits retrieval filters (relevant traditions, languages, optional date range).
2. **Retrieval** — hybrid dense + sparse search fused by Reciprocal Rank Fusion, reranked by a cross-encoder, then **diversified**: near-duplicate passages are collapsed, each requested tradition is guaranteed a minimum number of slots (a *per-tradition floor*), and no single work may dominate (a *per-source cap*). This is what stops a comparative answer from being silently monopolised by one or two traditions.
3. **Synthesis** — writes a grounded comparative analysis using only the retrieved passages, citing each claim with a positional `[SOURCE N]` marker and refusing to fill gaps from outside knowledge.
4. **Proofreading** — a deterministic structural check (does every `[SOURCE N]` resolve to a real chunk?) plus an LLM judge that verifies each claim against the English translation it cites, flagging unsupported claims, misattribution, anachronism, and over-translation. A genuine recall gap can route back to Retrieval, capped at two corrective passes.
5. **Citation** — formats per-tradition academic references from metadata and embeds the **original text and English translation** of every cited passage, so each citation is verifiable from the output alone.

---

## What Makes It Different: Traceable Provenance

Most RAG systems hand you an answer and a vague list of sources. This one gives you a **complete, auditable chain** from claim to text:

- **Positional citation resolution** — every `[SOURCE N]` in the prose is mapped back to a concrete `chunk_id`, `source_urn` (Perseus CTS where available), section, and tradition.
- **Two-layer verification** — a deterministic integrity check guarantees no citation points at a non-existent source; an LLM judge checks that each cited passage actually supports its claim.
- **Original + translation in every citation** — you see exactly what the Greek, Chinese, or Latin said, and its English rendering.
- **Per-run JSONL traces** — query, expanded terms, every retrieved chunk with score, the draft, the final answer, resolved citations, and per-claim verifications, written to one timestamped file per run.
- **Dated answer exports** — a clean, shareable Markdown answer stamped with the **date of input**.

---

## Example Run & Results

The repository ships a reproducible probe suite — **16 questions** designed to test
the system's capabilities *and its limits*, because a grounded system has to know
when to decline. Run it yourself:

```bash
./run_test_suite.sh --list     # preview the questions
./run_test_suite.sh            # full battery (~20–25 min on GPU)
./run_test_suite.sh 7 8 12     # spot-check just the limit tests
```

Each run writes a trace, an answer export, and a `test_runs/<timestamp>/summary.tsv`.
The results below are from a sample run (2026-06-29, qwen3:14b, RTX 4070 Ti SUPER).
They are reported **honestly** — including what the system got wrong — because the
whole point of this project is provenance you can trust.

### What the run validates

- **Cross-lingual retrieval works.** Every comparative query retrieved relevant
  passages from all three traditions; a query written **entirely in Chinese**
  (黄帝内经…) still retrieved Suwen and produced a cited answer.
- **The per-tradition diversification floor holds.** All three traditions appeared
  in the retrieved set for every comparative question, and the three-way synthesis
  cited sources spread across all of them — the behaviour the floor was built to
  guarantee.
- **The self-correction loop fires.** The Chinese-language query triggered a second
  retrieval pass (`iterations = 2`) when the proofreader signalled a gap.
- **Near-duplicate collapse works.** The heavily-chunked *On Ancient Medicine* query
  cited only two distinct sources — no repeated-section pile-up.
- **The proofreader is not a rubber stamp.** It returned **not-passed on 4 of 16
  runs**, flagging weak or unsupported synthesis rather than approving everything —
  the verification layer doing its job.

### Selected results

| # | Probe | Retrieved | Cited | Proofread | Reading |
|---|-------|-----------|-------|-----------|---------|
| 3 | Causae on its strong vocabulary | all 3 | 5 sources | passed | Causae retrieved and cited richly — the previously-crowded-out tradition surfaces well |
| 5 | Three-tradition seasonal synthesis | all 3 | 7 sources | passed | Floor working; balanced citation across traditions |
| 6 | Term fidelity (qì / physis / viriditas) | all 3 | 7 sources | passed | Original-language terms attributed per tradition |
| 7 | **Limit:** antibiotics (absent) | all 3 | 4 sources | passed | Grounds against what *is* present to establish the gap (confirm wording in answer file) |
| 8 | **Limit:** microscope (anachronism) | all 3 | all 12 | passed | ⚠ cited every source — inspect the answer; possible over-citation |
| 11 | **Limit:** blood circulation (anachronism) | all 3 | 5 sources | passed | Confirm it does not project Harvey onto the texts |
| 13 | Causae seasonal/cosmological | all 3 | 0 sources | not passed | Honest "too thin" — no citations produced; structural check flagged it |
| 14 | Duplicate-section stress (OAM) | all 3 | 2 sources | passed | Dedup effective |
| 15 | Non-English (Chinese) query | all 3 | 5 sources | passed (2 iters) | Multilingual input + slug fallback both work |

### Known limitations surfaced by the run

Documented openly so users know the edges:

- **Temporal filtering is unreliable (#12).** A query restricted to "sources after
  1000 CE" should have narrowed to *Causae et Curae* alone, but all three traditions
  were still retrieved — the query analyser did not convert the phrase into a numeric
  date filter. Date-scoped queries should not be relied on yet.
- **Single-tradition isolation can leak (#1).** A Suwen-only query admitted a
  medieval passage, because the keyword (BM25) path is not tradition-filtered the way
  the dense path is. The final answer still focused on Suwen, but retrieval was not
  cleanly isolated.
- **Anachronism handling needs answer-level review (#8, #11).** The structured signals
  look reasonable, but confirming that the system *names the anachronism and declines*
  — rather than answering around it — requires reading the per-question answer files in
  `test_runs/<timestamp>/`.

> **On reproducibility:** qwen3:14b is non-deterministic, so exact citations and
> pass/fail will vary between runs. The qualitative behaviour — correct cross-lingual
> retrieval, balanced traditions, an active proofreader, and the limitations above —
> should reproduce.

---

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 4-core modern CPU | 8-core modern CPU |
| **RAM** | 16 GB | 32 GB |
| **GPU** *(optional)* | — | NVIDIA GPU 12 GB+ VRAM (offloads qwen3:14b, large speedup) |
| **Storage** | 50 GB free | 50 GB free |
| **OS** | Ubuntu 20.04 / 22.04 LTS | Ubuntu 22.04 LTS |
| **Python** | 3.10 or 3.11 | 3.11 |
| **Docker** | Required (Qdrant + Elasticsearch) | Required |

The system is designed to run **CPU-only and fully offline**. A GPU is optional: with enough VRAM, Ollama offloads `qwen3:14b` and inference is markedly faster.

---

## Installation

### Prerequisites
Docker, Python 3.10/3.11, and Git.

### Full Build Sequence

```bash
# 1. System dependencies
sudo apt update && sudo apt install -y build-essential git curl wget \
  python3.11 python3.11-venv python3-pip default-jdk docker.io docker-compose-plugin

# 2. Project setup
cd ~/histmed_rag && python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Download source texts (internet required, once)
python scripts/download_suwen.py
#   Hippocrates: place the Perseus TEI/parallel-English sources in corpus/raw/
#   Causae et Curae: place the OCR'd Latin source in corpus/raw/

# 4. Download models (internet required, once)
python3 -c "from FlagEmbedding import BGEM3FlagModel; BGEM3FlagModel('BAAI/bge-m3')"
python3 -c "from FlagEmbedding import FlagReranker; FlagReranker('BAAI/bge-reranker-v2-m3')"
ollama pull qwen3:14b

# 5. Preprocess each corpus into corpus/processed/*.jsonl
python scripts/preprocess_suwen.py          # → suwen_chunks.jsonl
python scripts/preprocess_hippocrates.py    # → hippocrates_chunks.jsonl
python scripts/preprocess_causae_txt.py     # → causaecurae_chunks.jsonl

# 6. Translate non-English chunks to English (one-time, idempotent, local LLM)
python scripts/translate_chunks.py          # adds text_translation to Suwen & Causae

# 7. Start infrastructure
docker compose -f docker/docker-compose.yml up -d
ollama serve &
python scripts/setup_qdrant.py

# 8. Build the indexes (run in this order)
python scripts/index_corpus.py              # Qdrant dense index (RECREATE=True)
python scripts/index_elasticsearch.py       # Elasticsearch BM25 index

# 9. Ready — see Quick Start
./start.sh
```

> **Pipeline order matters.** Preprocess → **translate** → index. Retrieval embeds and reranks on the English translation, so `translate_chunks.py` must run before `index_corpus.py`. If you re-translate, re-index both stores.

---

## Quick Start

The included **`start.sh`** brings everything up in the right order and waits for each service to be healthy before launching:

```bash
cd ~/histmed_rag
./start.sh                                   # interactive prompt
./start.sh "How do the three traditions explain seasonal disease onset?"   # one-shot
```

`start.sh` will: activate the venv → start Qdrant + Elasticsearch → start Ollama if needed → wait for ports `6333`, `9200`, `11434` → ensure `qwen3:14b` is pulled → launch `main.py`.

To run manually:

```bash
source venv/bin/activate
docker compose -f docker/docker-compose.yml up -d
ollama serve &
python main.py "Compare qì in Chinese medicine and the humoral balance in Greek medicine"
```

---

## Usage

**Command line**

```bash
python main.py "How do the three traditions explain the relationship between seasonal change and disease onset?"
# or, with no argument, you'll be prompted to type a query
python main.py
```

**From Python**

```python
from main import query

answer = query("Compare the role of heat and cold in Greek and Chinese accounts of disease")
print(answer)   # the final, cited, proofread synthesis
```

Each run prints the comparative answer with inline `[SOURCE N]` citations, a **References** section containing each source's original text and English translation, and a proofreading summary — then writes a trace and an answer export (below).

**Query tips**

- Be specific and comparative: *"How does **each** tradition explain epilepsy?"* beats *"epilepsy"*.
- Use period vocabulary — *humors, qì, physis, temperaments, melancholy* — to anchor retrieval.
- General/comparative queries automatically engage the per-tradition floor so all requested traditions are represented; a single-tradition query is hard-filtered to that tradition.

---

## Outputs: Traces & Answer Exports

Every run produces two timestamped artifacts, both named by **date of input** (captured at submission, not completion):

```
logs/2026-06-28_190436_how-do-the-three-traditions_ccf2b265.jsonl   # machine-readable trace
exports/2026-06-28_190436_how-do-the-three-traditions_ccf2b265.md   # human-readable answer
```

- **Trace (`logs/*.jsonl`)** — one complete JSON record per run: user + expanded query, every retrieved chunk with its rerank score and provenance, the synthesis draft, the final answer, resolved citations (with full original + translation), and per-claim verification results. One file per run, so no run is ever overwritten. Read them all with a glob:

  ```bash
  # latest trace, cited sources only
  python3 -c "import json,glob,os; f=max(glob.glob('logs/*.jsonl'),key=os.path.getmtime); r=json.loads(open(f).read()); print(f); print('cited:', r['cited_source_ns'])"
  ```

- **Answer export (`exports/*.md`)** — a clean, shareable Markdown file: date of input, the query, and the full cited answer. The short id in the filename matches its trace.

---

## Verify the Index

After indexing, confirm all three counts agree (≈ **1,224** chunks):

```bash
# 1. Source of truth — non-empty lines across the processed corpora
cat corpus/processed/*.jsonl | grep -c .

# 2. Qdrant dense vectors
python3 -c "from qdrant_client import QdrantClient; print(QdrantClient(host='localhost',port=6333).count('histmed_corpus').count)"

# 3. Elasticsearch documents
curl -s localhost:9200/histmed_corpus/_count
```

If the JSONL count exceeds either index, an index run was incomplete or stale — re-run `index_corpus.py` then `index_elasticsearch.py`.

---

## Project Structure

```
~/histmed_rag/
├── venv/
├── corpus/
│   ├── raw/                            # original source files (Suwen, Hippocrates TEI, Causae OCR)
│   └── processed/
│       ├── suwen_chunks.jsonl
│       ├── hippocrates_chunks.jsonl
│       └── causaecurae_chunks.jsonl
├── models/                             # cached BGE-M3 + BGE-reranker-v2-m3
├── scripts/
│   ├── download_suwen.py
│   ├── preprocess_suwen.py
│   ├── preprocess_hippocrates.py       # Greek + English section-aligned parser
│   ├── preprocess_causae_txt.py
│   ├── translate_chunks.py             # one-time local LLM translator (idempotent)
│   ├── setup_qdrant.py
│   ├── index_corpus.py                 # Qdrant dense indexer
│   ├── index_elasticsearch.py          # Elasticsearch BM25 indexer
│   └── retrieval.py                    # HybridRetriever (dense + BM25 + RRF + rerank + diversify)
├── agents/
│   ├── state.py                        # LangGraph AgentState (TypedDict)
│   ├── nodes.py                        # the five agents + citation resolution/verification
│   ├── graph.py                        # compiled LangGraph state machine
│   ├── trace_logger.py                 # per-run JSONL provenance traces
│   └── answer_exporter.py              # dated Markdown answer exports
├── docker/
│   └── docker-compose.yml              # Qdrant + Elasticsearch
├── config/
│   └── settings.py
├── logs/                               # one timestamped trace per run
├── exports/                            # one timestamped answer per run
├── main.py                             # entry point
├── start.sh                            # startup orchestration
├── requirements.txt
└── README.md
```

---

## Technical Notes

**Embeddings — BGE-M3.** Multilingual dense vectors (1024-dim). Each chunk is embedded as *translation + original*, so English queries match a non-English corpus.

**Vector store — Qdrant.** Cosine ANN search over the dense vectors; metadata filters on tradition, language, and numeric date. Stable, deterministic point IDs (`uuid5`) make re-indexing reproducible.

**Keyword store — Elasticsearch.** BM25 (k1=1.5, b=0.75) over the English translation (boosted), original text, and section. Complements semantic search for exact terms and locators.

**Fusion + rerank.** Dense and sparse result lists are merged by Reciprocal Rank Fusion, then a **BGE-reranker-v2-m3** cross-encoder rescores the pool against the English text. Final selection applies near-duplicate collapse, a per-tradition floor, and a per-source cap.

**Generation — Ollama + qwen3:14b.** A Qwen3-aware local call uses `num_ctx=16384`, strips the model's `<think>` reasoning from visible output, and constrains JSON-emitting agents to valid JSON. Runs CPU-only; offloads to GPU when available.

**Orchestration — LangGraph.** A typed `AgentState` is threaded through five nodes; the proofreader can conditionally route back to retrieval (capped at two passes) when a real recall gap is detected.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Connection refused (6333 / 9200)** | Services still starting. `start.sh` waits for them; if running manually, give Docker a moment after `up -d`. |
| **Out of memory** | Lower `EMBED_BATCH_SIZE` in `index_corpus.py`; run qwen3:14b CPU-only; close other apps. |
| **Docker won't start** | `sudo systemctl start docker` and confirm your user is in the `docker` group. |
| **Ollama not responding** | `ollama serve &`, then `ollama list` to confirm `qwen3:14b` is present. |
| **A tradition is missing from answers** | Expected behaviour is the per-tradition floor; check the latest trace's retrieved traditions. If truly absent, re-verify the index counts. |
| **Index counts disagree** | Re-run `index_corpus.py` then `index_elasticsearch.py` (translate first if translations changed). |
| **No results** | Broaden the query or remove date filters. |

---

## Citing the System

```bibtex
@software{histmed_rag,
  author = {Bingzhi Wang},
  title  = {Historical Medical RAG: Cross-Cultural Analysis of Ancient Medical Texts},
  year   = {2026},
  url    = {https://github.com/bingzhi-wang/histmed_rag}
}
```

When quoting any passage surfaced by the system, cite the **original work** (and Perseus CTS URN for the Hippocratic texts) shown in the references — and remember that the Chinese and Latin English are machine translations.

---

## License

MIT — see [LICENSE](LICENSE).

---

*Three traditions. Three languages. Fifteen centuries. One question at a time — and a citation for every word.*
