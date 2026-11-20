#!/bin/bash
cd "$(dirname "$0")"
bundle install
ENCRYPT_PAYLOADS=$1 bundle exec ruby worker.rb
