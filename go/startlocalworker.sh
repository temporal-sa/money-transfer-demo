#!/bin/bash
cd "$(dirname "$0")"
ENCRYPT_PAYLOADS=$1 go run worker/main.go
