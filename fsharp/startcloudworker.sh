#!/bin/bash
cd "$(dirname "$0")"
source ../setcloudenv.sh
cd src
ENCRYPT_PAYLOADS=$1 dotnet run
