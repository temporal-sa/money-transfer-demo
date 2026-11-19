/// Payloads and scenarios shared by the workflows and activities.
///
/// The JSON names on these records are the wire contract with the Java UI
/// (see ui/src/main/java/.../model), so they must not change.
module MoneyTransfer.Model

open System
open System.Text.Json.Serialization
open Temporalio.Common
open Temporalio.Workflows

[<Literal>]
let TaskQueue = "MoneyTransfer" // default; override with TEMPORAL_MONEYTRANSFER_TASKQUEUE

type TransferInput =
    { [<JsonPropertyName "amount">] Amount: int
      [<JsonPropertyName "fromAccount">] FromAccount: string
      [<JsonPropertyName "toAccount">] ToAccount: string }

type DepositResponse =
    { [<JsonPropertyName "chargeId">] ChargeId: string }

type TransferOutput =
    { [<JsonPropertyName "depositResponse">] DepositResponse: DepositResponse }

type TransferStatus =
    { [<JsonPropertyName "progressPercentage">] ProgressPercentage: int
      [<JsonPropertyName "transferState">] TransferState: string
      [<JsonPropertyName "workflowStatus">] WorkflowStatus: string
      [<JsonPropertyName "chargeResult">] ChargeResult: DepositResponse
      [<JsonPropertyName "approvalTime">] ApprovalTime: int }

module TransferStatus =
    let initial approvalTime =
        { ProgressPercentage = 0
          TransferState = "starting"
          WorkflowStatus = ""
          ChargeResult = { ChargeId = "" }
          ApprovalTime = approvalTime }

/// Passed from the workflow to the Withdraw and Deposit activities.
/// `Type` carries the raw workflow type so activities can simulate a scenario.
type ActivityInput =
    { [<JsonPropertyName "idempotencyKey">] IdempotencyKey: string
      [<JsonPropertyName "amount">] Amount: int
      [<JsonPropertyName "type">] Type: string }

/// The demo scenarios. The UI picks one by starting a workflow of the matching type.
type Scenario =
    | HappyPath
    | AdvancedVisibility
    | HumanInLoop
    | ApiDowntime
    | BugInWorkflow
    | InvalidAccount

module Scenario =
    let ofWorkflowType =
        function
        | "AccountTransferWorkflowAdvancedVisibility" -> AdvancedVisibility
        | "AccountTransferWorkflowHumanInLoop" -> HumanInLoop
        | "AccountTransferWorkflowAPIDowntime" -> ApiDowntime
        | "AccountTransferWorkflowRecoverableFailure" -> BugInWorkflow
        | "AccountTransferWorkflowInvalidAccount" -> InvalidAccount
        | _ -> HappyPath

    /// Does this scenario record its progress in the `Step` search attribute?
    let tracksStep scenario = scenario = AdvancedVisibility

    /// Does this scenario wait for a human to approve the transfer?
    let needsApproval scenario = scenario = HumanInLoop

/// Every activity uses the same timeout and retry policy.
let activityOptions =
    ActivityOptions(
        StartToCloseTimeout = TimeSpan.FromSeconds 5.0,
        RetryPolicy =
            RetryPolicy(
                InitialInterval = TimeSpan.FromSeconds 1.0,
                MaximumInterval = TimeSpan.FromSeconds 30.0,
                BackoffCoefficient = 2.0f
            )
    )
