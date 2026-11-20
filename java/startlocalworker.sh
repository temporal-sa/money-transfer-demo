#!/bin/bash
cd "$(dirname "$0")"
ENCRYPT_PAYLOADS=$1 ./gradlew run --console=plain
