#!/bin/bash
bundle install
ENCRYPT_PAYLOADS=$1 bundle exec ruby worker.rb
