# Historical Medical RAG System
## Cross-Cultural Analysis of Ancient Medical Texts

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-required-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ollama](https://img.shields.io/badge/ollama-supported-000000.svg)](https://ollama.ai/)

A fully offline, agentic Retrieval-Augmented Generation (RAG) system for cross-cultural historical medical research. Compare ancient Greek, classical Chinese, and medieval European medical texts without any internet connection or API costs.

## 📋 Table of Contents
- [Overview](#overview)
- [System Architecture](#system-architecture)
- [The Three Corpus Texts](#the-three-corpus-texts)
- [Hardware Requirements](#hardware-requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [User Guide](#user-guide)
- [Project Structure](#project-structure)
- [Technical Documentation](#technical-documentation)
- [License](#license)

## Overview

This system enables comparative analysis of three foundational medical texts:
- **黄帝内经素問 (Huángdì Nèijīng Sùwèn)** - Classical Chinese medicine
- **Περὶ Νούσων (Peri Nouson/De Morbis)** - Ancient Greek medicine
- **Causae et Curae** - Medieval European medicine

The system runs entirely on your local machine, providing:
- 🔒 **Complete privacy** - No data leaves your computer
- 💰 **Zero API costs** - All models run locally
- 🌐 **No internet required** - Fully offline after setup
- 🧠 **Intelligent agents** - LangGraph orchestrates complex research queries

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER QUERY INPUT                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              QUERY ANALYSIS AGENT                           │
│  - Term expansion across languages/periods                  │
│  - Query refinement and decomposition                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              RETRIEVAL AGENT                                │
│  ┌────────────────────────────────────────────────────┐     │
│  │  Dense Vector Search (Qdrant + BGE-M3)            │     │
│  │  Keyword Search (Elasticsearch BM25)              │     │
│  │  Reciprocal Rank Fusion (RRF)                     │     │
│  │  Cross-Encoder Reranking                          │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              SYNTHESIS AGENT                               │
│  - Generates comparative analysis                         │
│  - Cross-cultural medical insights                        │
│  - Synthesizes findings across traditions                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              PROOFREADING AGENT                            │
│  - Verifies claims against sources                         │
│  - Checks accuracy of citations                            │
│  - Ensures scholarly rigor                                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              CITATION AGENT                                │
│  - Formats academic citations                              │
│  - Provides full provenance metadata                       │
└─────────────────────────────────────────────────────────────┘
```

## The Three Corpus Texts

| Text | Language/Period | Focus |
|------|----------------|-------|
| **黄帝内经素問 (Huángdì Nèijīng Sùwèn)** | Classical Chinese ~300-100 BCE | Qi, five phases, yin-yang pathology, seasonal medicine |
| **Περὶ Νούσων I–II (Peri Nouson/De Morbis)** | Ancient Greek ~420-370 BCE | Humoral theory, disease typology, physis, prognosis |
| **Causae et Curae (Hildegard von Bingen)** | Medieval Latin ~1150-1160 CE | Humoral-cosmological disease, temperaments, remedies |

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 4-core modern CPU | 8-core modern CPU |
| **RAM** | 16 GB | 32 GB |
| **GPU** (optional) | NVIDIA GPU with 6GB+ VRAM | Speeds up inference |
| **Storage** | 50 GB free | 50 GB free |
| **OS** | Ubuntu 20.04/22.04 LTS | Ubuntu 22.04 LTS |
| **Python** | 3.10 or 3.11 | 3.11 |
| **Docker** | Required | Required |

## Installation

### Prerequisites
Ensure you have Docker, Python 3.10/3.11, and Git installed.

### Full Build Sequence

```bash
# 1. System dependencies
sudo apt update && sudo apt install -y build-essential git curl wget \
  python3.11 python3.11-venv python3-pip default-jdk docker.io docker-compose

# 2. Project setup
cd ~/histmed_rag && python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Download texts (requires internet, once only)
python scripts/download_suwen.py
cd corpus/raw/perinouson && wget [perseus URLs] && cd ../../..

# 4. Download models (requires internet, once only)
python3 -c "from FlagEmbedding import BGEM3FlagModel; BGEM3FlagModel('BAAI/bge-m3')"
python3 -c "from FlagEmbedding import FlagReranker; FlagReranker('BAAI/bge-reranker-v2-m3')"
ollama pull mistral:7b-instruct-q4_0

# 5. Preprocess corpus
python scripts/preprocess_suwen.py
python scripts/preprocess_perinouson.py
python scripts/preprocess_causae.py

# 6. Start infrastructure
cd docker && docker-compose up -d && cd ..
ollama serve &

# 7. Index corpus
python scripts/setup_qdrant.py
python scripts/index_corpus.py
python scripts/index_elasticsearch.py

# 8. System is ready!
python main.py
```

## Quick Start

### Step 1: Start the System
```bash
cd ~/histmed_rag
source venv/bin/activate
docker-compose -f docker/docker-compose.yml up -d
ollama serve &
python main.py
```

### Step 2: Run Your First Query
```python
# Example query
query = "Compare the concepts of 'qi' in Chinese medicine and 'pneuma' in Greek medicine"
result = agent_chain.invoke({"query": query})
print(result)
```

### Step 3: Advanced Queries
```python
# Cultural comparison
query = "How do Chinese five phases and Greek humoral theory approach seasonal diseases?"

# Specific text analysis
query = "What does Causae et Curae say about the relationship between seasons and diseases?"

# Cross-cultural synthesis
query = "Compare diagnostic methods across all three medical traditions"
```

## User Guide

### Basic Usage Patterns

#### 1. Comparative Query
```python
response = system.query("Compare the treatment of fever in Chinese and Greek medicine")
print(response["analysis"])
print(response["citations"])
```

#### 2. Single Text Exploration
```python
response = system.query(
    "Explain the concept of physis in Peri Nouson",
    filter={"source": "perinouson"}
)
```

#### 3. Cross-Cultural Synthesis
```python
response = system.query("Synthesize the role of the four elements in all three traditions")
```

### Query Tips

1. **Be Specific** - "Compare lung diseases" vs "How do each tradition explain lung diseases?"
2. **Use Medical Terminology** - "humors", "qi", "physis", "temperaments"
3. **Request Citations** - Always verify claims against sources
4. **Filter by Text** - Use `filter={"source": "text_name"}` for focused analysis

### Example Use Cases

| Use Case | Query Example | Expected Output |
|----------|--------------|-----------------|
| **Disease Comparison** | "How do the three traditions explain epilepsy?" | Cultural comparison with citations |
| **Concept Analysis** | "What is the concept of 'balance' across all texts?" | Synthesis with textual evidence |
| **Seasonal Medicine** | "Compare seasonal disease theories" | Parallel analysis with examples |
| **Treatment Approaches** | "How do different traditions approach pneumonia?" | Comparative treatment methods |

## Project Structure

```
~/histmed_rag/
├── venv/                          # Python virtual environment
├── corpus/
│   ├── raw/
│   │   ├── suwen/                 # Raw Suwen chapter files
│   │   ├── perinouson/            # TEI-XML Greek files
│   │   └── causaecurae/           # Latin source files
│   └── processed/
│       ├── suwen_chunks.jsonl
│       ├── perinouson_chunks.jsonl
│       └── causaecurae_chunks.jsonl
├── models/
│   ├── embeddings/bge-m3/         # BGE-M3 embedding model
│   └── reranker/bge-reranker-v2-m3/
├── scripts/
│   ├── download_suwen.py
│   ├── preprocess_suwen.py
│   ├── preprocess_perinouson.py
│   ├── preprocess_causae.py
│   ├── setup_qdrant.py
│   ├── index_corpus.py
│   ├── index_elasticsearch.py
│   └── retrieval.py               # HybridRetriever class
├── agents/
│   ├── state.py                   # LangGraph state definition
│   ├── nodes.py                   # All five agent functions
│   └── graph.py                   # Compiled LangGraph graph
├── docker/
│   └── docker-compose.yml         # Qdrant + Elasticsearch
├── config/
│   └── settings.py
├── logs/
├── main.py                        # Entry point
├── start.sh                       # System startup script
└── requirements.txt
└── README.md
```

## Technical Documentation

### Core Components

#### 1. **BGE-M3 Embedding Model**
- Multilingual support (Chinese, Greek, Latin, English)
- Dense retrieval with 1024-dimension vectors
- Runs locally on CPU/GPU

#### 2. **Qdrant Vector Database**
- Stores semantic embeddings
- Fast approximate nearest neighbor search
- Docker containerized for easy management

#### 3. **Elasticsearch BM25**
- Keyword-based retrieval
- Complements semantic search
- Hybrid retrieval improves accuracy

#### 4. **Cross-Encoder Reranking**
- BGE-reranker-v2-m3
- Improves retrieval precision
- Reranks top candidates

#### 5. **Ollama + Mistral 7B**
- Quantized language model
- 7B parameters for fast inference
- CPU-compatible with decent performance

#### 6. **LangGraph Agents**
- State-machine based orchestration
- Multi-step reasoning
- Error handling and fallbacks

### Performance Optimization

1. **GPU Acceleration**
   ```bash
   # Enable GPU for embeddings
   export CUDA_VISIBLE_DEVICES=0
   python main.py --use_gpu
   ```

2. **Memory Optimization**
   ```python
   # Reduce batch size for memory-constrained systems
   config = {"batch_size": 32, "chunk_size": 512}
   ```

3. **Faster Inference**
   ```bash
   # Use smaller model variant
   ollama pull mistral:7b-instruct-q4_0
   ```

### Troubleshooting Guide

| Issue | Solution |
|-------|----------|
| **Out of Memory** | Reduce batch size, use CPU-only mode |
| **Docker fails to start** | Ensure Docker is running: `sudo systemctl start docker` |
| **Ollama not responding** | Restart: `ollama serve &` |
| **Slow retrieval** | Use keyword-only search: `search_type='keyword'` |
| **No results found** | Broaden query or remove language filters |

### Citing the System

When using this system in academic research, please cite:

```bibtex
@software{histmed_rag,
  author = {[Bingzhi Wang]},
  title = {Historical Medical RAG: Cross-Cultural Analysis of Ancient Medical Texts},
  year = {2026},
  url = {https://github.com/bingzhi-wang/histmed_rag}
}
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

