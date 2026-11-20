# Usage: ./sendapproval.sh <workflowId>
#   e.g. ./sendapproval.sh TRANSFER-EZF-249
./gradlew -q execute -PmainClass=io.temporal.samples.moneytransfer.TransferApprover -Parg=$1
