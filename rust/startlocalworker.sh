#!/bin/bash
cd "$(dirname "$0")"
cargo build --bin worker
ENCRYPT_PAYLOADS=$1 ./target/debug/worker
