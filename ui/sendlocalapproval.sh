#!/bin/bash
# Usage: ./sendlocalapproval.sh <workflowId> [encryptPayloads]
#   e.g. ./sendlocalapproval.sh TRANSFER-EZF-249 true
# Pass "true" as the second argument if the worker encrypts payloads.
echo off
ENCRYPT_PAYLOADS=$2 ./gradlew -q execute -PmainClass=io.temporal.samples.moneytransfer.TransferApprover -Parg=$1
