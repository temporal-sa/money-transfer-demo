#!/bin/bash
cd "$(dirname "$0")"
if [ ! -f ../setcloudenv.sh ]; then
  echo "error: ../setcloudenv.sh not found. Copy setcloudenv.example to setcloudenv.sh and fill in your Temporal Cloud settings." >&2
  exit 1
fi
source ../setcloudenv.sh
bundle install
ENCRYPT_PAYLOADS=$1 bundle exec ruby worker.rb
