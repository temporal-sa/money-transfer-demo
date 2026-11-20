#!/bin/bash
cd "$(dirname "$0")"
if [ ! -f ../setcloudenv.sh ]; then
  echo "error: ../setcloudenv.sh not found. Copy setcloudenv.example to setcloudenv.sh and fill in your Temporal Cloud settings." >&2
  exit 1
fi
source ../setcloudenv.sh
npm install
ENCRYPT_PAYLOADS=$1 npm run start.watch
