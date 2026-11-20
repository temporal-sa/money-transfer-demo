#!/bin/bash
# Usage: ./sendcloudapproval.sh <workflowId> [encryptPayloads]
#   e.g. ./sendcloudapproval.sh TRANSFER-EZF-249 true
# Pass "true" as the second argument if the worker encrypts payloads.
source ../setcloudenv.sh
ENCRYPT_PAYLOADS=$2 ./gradlew -q execute -PmainClass=io.temporal.samples.moneytransfer.TransferApprover -Parg=$1
