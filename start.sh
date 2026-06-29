#!/usr/bin/env bash
# start.sh — bring up infrastructure and launch the Historical Medical RAG system.
#
# Usage:
#   ./start.sh                      # interactive query prompt
#   ./start.sh "your query here"    # one-shot query
#
# Brings up Qdrant + Elasticsearch (Docker) and Ollama, waits for each to be
# reachable, ensures the model is present, then runs main.py.

set -euo pipefail
cd "$(dirname "$0")"

QDRANT_URL="http://localhost:6333"
ES_URL="http://localhost:9200"
OLLAMA_URL="http://localhost:11434"
MODEL="qwen3:14b"
COMPOSE_FILE="docker/docker-compose.yml"

# Prefer Docker Compose v2 ("docker compose"); fall back to v1 ("docker-compose").
if docker compose version >/dev/null 2>&1; then
  DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  DC="docker-compose"
else
  echo "ERROR: Docker Compose not found. Install docker-compose-plugin." >&2
  exit 1
fi

# 1. Activate the virtual environment
if [ -f venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
else
  echo "ERROR: venv not found." >&2
  echo "Run: python3.11 -m venv venv && source venv/bin/activate && pip install -r requirements.txt" >&2
  exit 1
fi

# 2. Start Qdrant + Elasticsearch
echo ">> Starting Qdrant + Elasticsearch ..."
$DC -f "$COMPOSE_FILE" up -d

# 3. Start Ollama only if it isn't already serving
if ! curl -s "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
  echo ">> Starting Ollama ..."
  ollama serve >/tmp/ollama.log 2>&1 &
fi

# 4. Wait for each service to become reachable
wait_for() {  # name url
  local name="$1" url="$2" tries=0
  printf ">> Waiting for %s " "$name"
  until curl -s "$url" >/dev/null 2>&1; do
    printf "."
    sleep 2
    tries=$((tries + 1))
    if [ "$tries" -ge 60 ]; then
      echo " timed out after 120s." >&2
      exit 1
    fi
  done
  echo " ok"
}

wait_for "Qdrant"        "$QDRANT_URL/readyz"
wait_for "Elasticsearch" "$ES_URL"
wait_for "Ollama"        "$OLLAMA_URL/api/tags"

# 5. Ensure the model is pulled (one-time)
if ! ollama list 2>/dev/null | grep -q "$MODEL"; then
  echo ">> Pulling $MODEL (one-time download) ..."
  ollama pull "$MODEL"
fi

# 6. Launch
echo ">> Launching HistMed RAG ..."
if [ "$#" -gt 0 ]; then
  python main.py "$@"
else
  python main.py
fi
