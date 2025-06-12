#!/bin/bash
bundle install
source ../setcloudenv.sh
ENCRYPT_PAYLOADS=$1 bundle exec ruby worker.rb
