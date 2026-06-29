#!/usr/bin/env bash
# run_test_suite.sh — run the HistMed RAG probe-question battery.
#
# Usage:
#   ./run_test_suite.sh                 # run all questions
#   ./run_test_suite.sh 5 7 11          # run only #5, #7, #11
#   ./run_test_suite.sh --list          # list questions, run nothing
#
# Requires the stack to be up (Qdrant 6333, Elasticsearch 9200, Ollama 11434).
# Bring it up first with ./start.sh in another terminal, or this script will
# warn and exit.

set -euo pipefail
cd "$(dirname "$0")"

# --list needs no services
if [ "${1:-}" != "--list" ]; then
  miss=0
  for url in "http://localhost:6333/readyz" "http://localhost:9200" "http://localhost:11434/api/tags"; do
    if ! curl -s "$url" >/dev/null 2>&1; then
      echo "WARN: service not reachable: $url" >&2
      miss=1
    fi
  done
  if [ "$miss" -ne 0 ]; then
    echo "One or more services are down. Start them with ./start.sh first." >&2
    exit 1
  fi
fi

# activate venv if present
if [ -f venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

python scripts/run_test_suite.py "$@"
