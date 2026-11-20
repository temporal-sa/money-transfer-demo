#!/bin/bash
cd "$(dirname "$0")"
cd src
ENCRYPT_PAYLOADS=$1 dotnet run
