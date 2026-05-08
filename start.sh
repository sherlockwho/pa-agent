#!/bin/bash
cd "$(dirname "$0")"
export OMP_NUM_THREADS=1
export TOKENIZERS_PARALLELISM=false
export TRANSFORMERS_OFFLINE=1
exec /opt/anaconda3/envs/pa-agent/bin/uvicorn \
  server.main:app \
  --reload \
  --reload-dir server \
  --host 0.0.0.0 \
  --port 8000
