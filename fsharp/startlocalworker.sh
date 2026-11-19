#!/bin/bash
cd "$(dirname "$0")/src"
ENCRYPT_PAYLOADS=$1 dotnet run
