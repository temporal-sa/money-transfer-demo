#!/bin/bash
cd "$(dirname "$0")"
npm install
ENCRYPT_PAYLOADS=$1 npm run start.watch
