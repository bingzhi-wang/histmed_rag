# Historical Medical RAG

*Three physicians — Chinese, Greek, and Medieval Latin — writing across 1,500 years and three languages, answering the same question side by side. With a citation for every word, and the honesty to say when a text stays silent.*

A fully offline research tool for the comparative history of medicine. Ask one question; read how three ancient traditions answer it, each grounded in its own sources. No internet, no API keys, no cloud.

## The three traditions

| Text | Tradition | Era |
|------|-----------|-----|
| **黄帝内经素問** (Huángdì Nèijīng Sùwèn) | Classical Chinese | ~300–100 BCE |
| **Hippocrates** — *On Ancient Medicine* & *Prognostic* | Ancient Greek | ~420–350 BCE |
| **Causae et Curae** (Hildegard von Bingen) | Medieval Latin | ~1150 CE |

## What it does

- **Answers comparatively.** One question returns a synthesis across all three traditions, never letting one drown out the others.
- **Reads across languages.** Ask in English (or Chinese); it finds the right Chinese, Greek, or Latin passage regardless.
- **Cites everything.** Every claim links to the exact passage it came from — original text *and* translation — so you can check the source yourself.
- **Knows when to stop.** If the texts don't address something, it says so plainly instead of inventing an answer.

## What it can't do (yet)

Stated openly, because trustworthy tools name their edges:

- **Date filters are unreliable.** "Sources after 1000 CE" won't reliably narrow to the medieval text.
- **Single-text isolation can leak.** A query meant for one tradition may still surface a passage from another.
- **Machine translation.** The Chinese and Latin English are LLM-translated (the Greek uses Perseus); every citation says so. Verify quotations against the original.

## Quick start

Requires Python 3.11, Docker, and [Ollama](https://ollama.ai/). After a one-time setup (see [INSTALL](#install)):

```bash
./start.sh "How do the three traditions explain seasonal disease?"
```

Each run prints a cited answer and saves it to `exports/` (a readable copy) and `logs/` (a full audit trail).

## How it works

A five-step pipeline — understand the question, retrieve passages, write a grounded synthesis, verify every citation, format the references. It runs locally on a quantized language model (qwen3:14b via Ollama) over hybrid search of the three corpora. *Curious about the internals? See [ARCHITECTURE.md](ARCHITECTURE.md).*

## Does it work?

A 16-question test suite (`./run_test_suite.sh`) probes both strengths and limits. In the sample run: all three traditions reliably retrieved and cited; cross-lingual and Chinese-language queries succeeded; the built-in proofreader actively rejected weak answers (4 of 16) rather than rubber-stamping; and the limitations above surfaced honestly. Full results live in `test_runs/`.

## Install

```bash
python3.11 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
python scripts/download_suwen.py            # + place Hippocrates & Causae sources in corpus/raw/
ollama pull qwen3:14b                        # + BGE-M3 and BGE-reranker-v2-m3 (see ARCHITECTURE.md)
python scripts/preprocess_suwen.py && python scripts/preprocess_hippocrates.py && python scripts/preprocess_causae_txt.py
python scripts/translate_chunks.py           # translate → then index (order matters)
docker compose -f docker/docker-compose.yml up -d
python scripts/index_corpus.py && python scripts/index_elasticsearch.py
```

Then `./start.sh`. Troubleshooting and verification: [ARCHITECTURE.md](ARCHITECTURE.md).

## Citing

```bibtex
@software{histmed_rag,
  author = {Bingzhi Wang},
  title  = {Historical Medical RAG: Cross-Cultural Analysis of Ancient Medical Texts},
  year   = {2026},
  url    = {https://github.com/bingzhi-wang/histmed_rag}
}
```

When quoting a passage, cite the original work shown in the references — and remember the Chinese and Latin English are machine translations.

## License

MIT — see [LICENSE](LICENSE).
