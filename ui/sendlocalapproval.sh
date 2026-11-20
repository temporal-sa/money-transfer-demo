#!/bin/bash
echo off
ENCRYPT_PAYLOADS=$2 ./gradlew -q execute -PmainClass=io.temporal.samples.moneytransfer.TransferApprover -Parg=$1
# where TRANSFER-EZF-249 is the workflowId
