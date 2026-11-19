namespace MoneyTransfer

open System
open System.Threading.Tasks
open Microsoft.Extensions.Logging
open Temporalio.Workflows
open MoneyTransfer.Model

/// The happy path: four steps, written as if nothing can go wrong.
/// Temporal provides the retries, timeouts and crash recovery.
///
/// Workflow code must be deterministic: use `task { }` (never `async { }`) and
/// Workflow.DelayAsync / Random / UtcNow (never Task.Delay, System.Random or
/// DateTime.Now). See ../PITFALLS.md.
[<Workflow("AccountTransferWorkflow")>]
type AccountTransferWorkflow() =
    let mutable status = TransferStatus.initial 0

    /// Pauses (durably) so the demo's progress bar is watchable, then records progress.
    let advance percent state (seconds: int) =
        task {
            if seconds > 0 then
                do! Workflow.DelayAsync(TimeSpan.FromSeconds(float seconds))
            status <- { status with ProgressPercentage = percent; TransferState = state }
        }

    [<WorkflowRun>]
    member _.Run(input: TransferInput) : Task<TransferOutput> =
        task {
            Workflow.Logger.LogInformation("Account Transfer workflow started, type = {Type}", Workflow.Info.WorkflowType)

            let activityInput =
                { IdempotencyKey = string (Workflow.Random.Next())
                  Amount = input.Amount
                  Type = Workflow.Info.WorkflowType }

            // The lambda names the activity to run; Temporal schedules it. The
            // result type (<string>) is needed to pick the right SDK overload.
            let! _ = Workflow.ExecuteActivityAsync<string>((fun () -> Activities.validate input), activityOptions)
            do! advance 25 "running" 1

            let! _ = Workflow.ExecuteActivityAsync<string>((fun () -> Activities.withdraw activityInput), activityOptions)
            do! advance 50 "running" 3

            let! deposit =
                Workflow.ExecuteActivityAsync<DepositResponse>((fun () -> Activities.deposit activityInput), activityOptions)
            status <- { status with ChargeResult = deposit }
            do! advance 75 "running" 1

            let! _ = Workflow.ExecuteActivityAsync<string>((fun () -> Activities.sendNotification input), activityOptions)
            do! advance 100 "finished" 0

            return { DepositResponse = deposit }
        }

    [<WorkflowQuery("transferStatus")>]
    member _.TransferStatus() = status
