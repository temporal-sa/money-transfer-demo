#!/bin/bash
source ../setcloudenv.sh
cargo build --bin worker
ENCRYPT_PAYLOADS=$1 ./target/debug/worker