/// Activities: the side-effecting steps of a transfer.
///
/// They are plain module functions. Temporal registers them as static
/// methods (see `moduleType`), so no class is needed.
module MoneyTransfer.Activities

open System.Threading.Tasks
open Microsoft.Extensions.Logging
open Temporalio.Activities
open Temporalio.Exceptions
open MoneyTransfer.Model

/// Lets the worker register every [<Activity>] function in this module.
type private Marker = class end
let moduleType = nonNull typeof<Marker>.DeclaringType

let private log () = ActivityExecutionContext.Current.Logger

/// Stands in for a call to an external banking API.
let private simulateCall (ms: int) = Task.Delay ms

/// The failure a scenario injects on a given attempt. Faults clear up from attempt 5 onwards.
type private Fault =
    | NoFault
    | ApiUnavailable
    | AccountInvalid

let private faultFor scenario attempt =
    match scenario, attempt with
    | _, attempt when attempt >= 5 -> NoFault
    | ApiDowntime, _ -> ApiUnavailable
    | InvalidAccount, _ -> AccountInvalid
    | _ -> NoFault

/// Simulates the call (faster on each retry) and reports which fault, if any, it hit.
let private callExternalApi (input: ActivityInput) =
    task {
        let attempt = ActivityExecutionContext.Current.Info.Attempt
        do! simulateCall (1000 / attempt)
        return faultFor (Scenario.ofWorkflowType input.Type) attempt
    }

[<Activity("Validate")>]
let validate (input: TransferInput) : Task<string> =
    task {
        log().LogInformation("Validate activity started, input = {Input}", input)
        do! simulateCall 1000
        return "SUCCESS"
    }

[<Activity("Withdraw")>]
let withdraw (input: ActivityInput) : Task<string> =
    task {
        log().LogInformation("Withdraw activity started, amount = {Amount}", input.Amount)

        match! callExternalApi input with
        | ApiUnavailable ->
            // A transient error: a plain exception is retried by Temporal.
            log().LogInformation("Withdraw API unavailable, attempt = {Attempt}", ActivityExecutionContext.Current.Info.Attempt)
            return failwith "Withdraw activity failed, API unavailable"
        | _ -> return "SUCCESS"
    }

[<Activity("Deposit")>]
let deposit (input: ActivityInput) : Task<DepositResponse> =
    task {
        log().LogInformation("Deposit activity started, amount = {Amount}", input.Amount)

        match! callExternalApi input with
        | AccountInvalid ->
            // A business error: retrying will not help, so mark it non-retryable.
            return raise (ApplicationFailureException("Deposit activity failed, account is invalid", nonRetryable = true))
        | _ -> return { ChargeId = "example-transfer-id" }
    }

[<Activity("SendNotification")>]
let sendNotification (input: TransferInput) : Task<string> =
    task {
        log().LogInformation("Send notification activity started, input = {Input}", input)
        do! simulateCall 1000
        return "SUCCESS"
    }

[<Activity("UndoWithdraw")>]
let undoWithdraw (amount: int) : Task<bool> =
    task {
        log().LogInformation("Undo withdraw activity started, amount = {Amount}", amount)
        do! simulateCall 1000
        return true
    }
