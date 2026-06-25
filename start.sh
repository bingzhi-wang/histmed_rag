#!/bin/bash
# start.sh — Start all HistMed RAG services

echo '=== Starting HistMed RAG System ==='
cd ~/histmed_rag

# 1. Start Docker containers
echo '→ Starting Qdrant and Elasticsearch...'
cd docker && docker-compose up -d && cd ..
sleep 5

# 2. Start Ollama
echo '→ Starting Ollama LLM server...'
ollama serve > logs/ollama.log 2>&1 &
sleep 3

# 3. Verify services
echo '→ Checking services...'
curl -s http://localhost:6333/healthz > /dev/null && echo '  ✓ Qdrant'
curl -s http://localhost:9200 > /dev/null && echo '  ✓ Elasticsearch'
curl -s http://localhost:11434/api/tags > /dev/null && echo '  ✓ Ollama'

echo ''
echo '=== All services running. System is offline-ready. ==='
echo 'Run: source venv/bin/activate && python main.py'
