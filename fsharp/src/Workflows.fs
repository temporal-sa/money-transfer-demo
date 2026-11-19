/// Workflows: the durable orchestration of a transfer.
///
/// Determinism rules for everything in this file:
///   * use `task { }`, never `async { }` (Async jumps to the thread pool and
///     escapes Temporal's deterministic scheduler)
///   * use Workflow.DelayAsync / WaitConditionAsync / Random / UtcNow, never
///     Task.Delay, Task.Run, System.Random or DateTime.Now
module MoneyTransfer.Workflows

open System
open System.Threading.Tasks
open Microsoft.Extensions.Logging
open Temporalio.Common
open Temporalio.Converters
open Temporalio.Exceptions
open Temporalio.Workflows
open MoneyTransfer.Model

/// Typed wrappers that schedule each activity. The lambda becomes a LINQ
/// expression that Temporal turns into a call to the named activity, so the
/// result type has to be given explicitly to pick the right overload.
module private Steps =
    let validate input =
        Workflow.ExecuteActivityAsync<string>((fun () -> Activities.validate input), activityOptions)

    let withdraw input =
        Workflow.ExecuteActivityAsync<string>((fun () -> Activities.withdraw input), activityOptions)

    let deposit input =
        Workflow.ExecuteActivityAsync<DepositResponse>((fun () -> Activities.deposit input), activityOptions)

    let sendNotification input =
        Workflow.ExecuteActivityAsync<string>((fun () -> Activities.sendNotification input), activityOptions)

    let undoWithdraw amount =
        Workflow.ExecuteActivityAsync<bool>((fun () -> Activities.undoWithdraw amount), activityOptions)

let private activityInputFor (input: TransferInput) =
    { IdempotencyKey = string (Workflow.Random.Next())
      Amount = input.Amount
      Type = Workflow.Info.WorkflowType }

/// Pauses (durably) so the demo's progress bar is watchable.
let private pause seconds =
    if seconds > 0 then
        Workflow.DelayAsync(TimeSpan.FromSeconds(float seconds))
    else
        Task.CompletedTask

/// The happy path: four steps, written as if nothing can go wrong.
/// Temporal provides the retries, timeouts and crash recovery.
[<Workflow("AccountTransferWorkflow")>]
type AccountTransferWorkflow() =
    let mutable status = TransferStatus.initial 0

    let advance percent state seconds =
        task {
            do! pause seconds
            status <- { status with ProgressPercentage = percent; TransferState = state }
        }

    [<WorkflowRun>]
    member _.Run(input: TransferInput) : Task<TransferOutput> =
        task {
            Workflow.Logger.LogInformation("Account Transfer workflow started, type = {Type}", Workflow.Info.WorkflowType)
            let activityInput = activityInputFor input

            let! _ = Steps.validate input
            do! advance 25 "running" 1

            let! _ = Steps.withdraw activityInput
            do! advance 50 "running" 3

            let! deposit = Steps.deposit activityInput
            status <- { status with ChargeResult = deposit }
            do! advance 75 "running" 1

            let! _ = Steps.sendNotification input
            do! advance 100 "finished" 0

            return { DepositResponse = deposit }
        }

    [<WorkflowQuery("transferStatus")>]
    member _.TransferStatus() = status

/// Every other scenario. It is a dynamic workflow, so it runs for any workflow
/// type the worker has no specific registration for. It parses the type into
/// a `Scenario` and switches behavior on that.
[<Workflow(Dynamic = true)>]
type AccountTransferWorkflowScenarios() =
    let approvalSeconds = 30
    let stepKey = SearchAttributeKey.CreateKeyword "Step"
    let mutable status = TransferStatus.initial approvalSeconds
    let mutable approved = false

    let advance percent state seconds =
        task {
            do! pause seconds
            status <- { status with ProgressPercentage = percent; TransferState = state }
        }

    let isWaiting () = status.TransferState = "waiting"

    /// AdvancedVisibility: publish the current step as a search attribute.
    let recordStep scenario (step: string) =
        if Scenario.tracksStep scenario then
            Workflow.Logger.LogInformation("Advanced visibility .. {Step}", step)
            Workflow.UpsertTypedSearchAttributes(stepKey.ValueSet step)

    /// HumanInLoop: wait (durably) for approval, or fail the transfer.
    let awaitApproval () =
        task {
            Workflow.Logger.LogInformation(
                "Waiting on 'approveTransfer' Signal or Update for workflow ID: {WorkflowId}",
                Workflow.Info.WorkflowId
            )
            do! advance 30 "waiting" 0

            match! Workflow.WaitConditionAsync((fun () -> approved), TimeSpan.FromSeconds(float approvalSeconds)) with
            | true -> ()
            | false ->
                Workflow.Logger.LogInformation(
                    "Approval not received within the {Seconds}-second time window: Failing the workflow.",
                    approvalSeconds
                )
                raise (ApplicationFailureException $"Approval not received within {approvalSeconds} seconds")
        }

    /// Deposit, or undo the withdrawal if the deposit fails for good (a saga).
    let depositOrCompensate (input: TransferInput) activityInput =
        task {
            let! result =
                task {
                    try
                        let! response = Steps.deposit activityInput
                        return Ok response
                    with :? ActivityFailureException as e ->
                        return Error e
                }

            match result with
            | Ok response -> return response
            | Error failure ->
                Workflow.Logger.LogInformation("Deposit failed unrecoverable error, reverting withdraw")
                let! _ = Steps.undoWithdraw input.Amount

                let reason =
                    match failure.InnerException with
                    | :? ApplicationFailureException as cause -> cause.Message
                    | _ -> failure.Message

                return raise (ApplicationFailureException reason)
        }

    [<WorkflowRun>]
    member _.Run(args: IRawValue[]) : Task<TransferOutput> =
        task {
            let input = Workflow.PayloadConverter.ToValue<TransferInput>(args[0])
            let scenario = Scenario.ofWorkflowType Workflow.Info.WorkflowType
            Workflow.Logger.LogInformation("Dynamic Account Transfer workflow started, scenario = {Scenario}", scenario)
            let activityInput = activityInputFor input

            recordStep scenario "Validate"
            let! _ = Steps.validate input
            do! advance 25 "running" 1

            if Scenario.needsApproval scenario then
                do! awaitApproval ()

            recordStep scenario "Withdraw"
            let! _ = Steps.withdraw activityInput
            do! advance 50 "running" 3

            if scenario = BugInWorkflow then
                // Not an ApplicationFailureException, so Temporal fails the
                // workflow *task* and keeps retrying it. Delete this line and
                // restart the worker: the workflow carries on where it left off.
                failwith "Simulate bug - fix me!"

            recordStep scenario "Deposit"
            let! deposit = depositOrCompensate input activityInput
            status <- { status with ChargeResult = deposit }
            do! advance 75 "running" 1

            recordStep scenario "Send Notification"
            let! _ = Steps.sendNotification input
            do! advance 100 "finished" 0

            return { DepositResponse = deposit }
        }

    [<WorkflowQuery("transferStatus")>]
    member _.TransferStatus() = status

    [<WorkflowSignal("approveTransfer")>]
    member _.ApproveTransferSignal() : Task =
        Workflow.Logger.LogInformation("Approve Signal Received")

        if isWaiting () then
            approved <- true
        else
            Workflow.Logger.LogInformation("Signal not applied: Transfer is not waiting for approval")

        Task.CompletedTask

    [<WorkflowUpdate("approveTransferUpdate")>]
    member _.ApproveTransferUpdate() : Task<string> =
        Workflow.Logger.LogInformation("Approve Update Validated: Approving Transfer")
        approved <- true
        Task.FromResult "successfully approved transfer"

    [<WorkflowUpdateValidator(nameof Unchecked.defaultof<AccountTransferWorkflowScenarios>.ApproveTransferUpdate)>]
    member _.ValidateApproveTransferUpdate() : unit =
        Workflow.Logger.LogInformation("Approve Update Received: Validating")

        if approved then
            invalidOp "Validation Failed: Transfer already approved"

        if not (isWaiting ()) then
            invalidOp "Validation Failed: Transfer doesn't require approval"
