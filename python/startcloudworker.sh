#!/bin/bash
cd "$(dirname "$0")"
if [ ! -f ../setcloudenv.sh ]; then
  echo "error: ../setcloudenv.sh not found. Copy setcloudenv.example to setcloudenv.sh and fill in your Temporal Cloud settings." >&2
  exit 1
fi
source ../setcloudenv.sh
poetry install --no-root
ENCRYPT_PAYLOADS=$1 poetry run python worker.py
