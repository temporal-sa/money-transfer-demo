# money-transfer-fsharp

A money transfer demo worker written in idiomatic F# on the Temporal .NET SDK
([`Temporalio`](https://www.nuget.org/packages/Temporalio)). It works with the Java UI,
so you can swap it in for any of the other language workers.

See the main [README](../README.md) for how to start Temporal and the UI.

## Run Worker Locally

```bash
./startlocalworker.sh
```

The first run restores NuGet packages and builds, which takes a few seconds. The
worker then polls the `MoneyTransfer` task queue on `127.0.0.1:7233`. Set
`TEMPORAL_MONEYTRANSFER_TASKQUEUE` to use a different task queue.

## Start Worker on Temporal Cloud

If you haven't set up `setcloudenv.sh` yet, follow the instructions in the main [README](../README.md).
It sets `TEMPORAL_ADDRESS` and `TEMPORAL_NAMESPACE`, plus either `TEMPORAL_API_KEY` or
`TEMPORAL_CERT_PATH` / `TEMPORAL_KEY_PATH`.

```bash
./startcloudworker.sh
```

If an API key is set, the worker uses it. Otherwise it uses mTLS. It refuses to start
against a non-local address without one of the two.

## Encrypting payloads

Pass `true` as the first argument to either script, and start the UI the same way
(`../ui/startlocalwebui.sh true` or `../ui/startcloudwebui.sh true`):

```bash
./startlocalworker.sh true
```

Payloads are AES-256-GCM encrypted with the same key and format as the other workers.
To read them in the Temporal Web UI, use the codec server at
[https://codec.tmprl-demo.cloud](https://codec.tmprl-demo.cloud), as described in the main README.

## Where to look

| File | What it shows |
|------|---------------|
| [`src/Model.fs`](src/Model.fs) | Payloads as immutable records, and the demo scenarios as a discriminated union (`Scenario`) parsed from the workflow type |
| [`src/Activities.fs`](src/Activities.fs) | Activities as plain module functions. No class is needed. Scenario faults come from a single `match` |
| [`src/Workflows.fs`](src/Workflows.fs) | The happy-path workflow, and a dynamic workflow that handles every other scenario: approval (signal + update), the bug, and a saga-style compensation |
| [`src/EncryptionCodec.fs`](src/EncryptionCodec.fs) | Optional payload encryption, byte-compatible with the other workers |
| [`src/Program.fs`](src/Program.fs) | Connection settings parsed into an `Auth` union (`Local` / `ApiKey` / `MTls`), then running the worker |
| [`PITFALLS.md`](PITFALLS.md) | F#-specific pitfalls with the .NET SDK: async in workflows, SDK interop, workflow classes, exceptions |

### Your domain in F#, durability from Temporal

Payloads, scenario logic and activities are ordinary F#: records, unions, pattern
matching, and `Result` for the deposit-or-compensate step. The only class-shaped code is
the two workflow types. Temporal finds workflows, queries, signals and updates through
attributes on a class, and the query/signal handlers share state with the running
workflow, so each workflow keeps one `let mutable status` (an immutable record that it
replaces on each step).

### Determinism rules for workflow code

Temporal recovers a workflow by replaying its history through your code, so workflow
code must make the same decisions every time it runs. In F# that means:

- Use **`task { }`**, never `async { }`. F# `Async` runs its own timers and thread
  switches outside Temporal's deterministic scheduler.
- Use `Workflow.DelayAsync`, `Workflow.WaitConditionAsync`, `Workflow.Random` and
  `Workflow.UtcNow`, never `Task.Delay`, `Task.Run`, `System.Random` or `DateTime.Now`.
- Never use `.ConfigureAwait(false)` in workflow code.
- Put I/O and anything non-deterministic in activities.

Activities are normal .NET code and can use anything they like.

**Read [PITFALLS.md](PITFALLS.md) before writing workflow code.** Some F# mistakes, such
as `Async.Sleep` in a workflow, make the workflow hang with no error anywhere. That page
lists them, along with other F#-specific pitfalls in the SDK.

### Calling activities

```fsharp
Workflow.ExecuteActivityAsync<string>((fun () -> Activities.validate input), activityOptions)
```

Temporal turns the lambda into a call to the `Validate` activity. Give the result type
(`<string>`) explicitly, because without it F# can't choose between the SDK's overloads.

## Scenarios

Select a scenario in the UI's "Debug: Simulate" box:

| Scenario | What happens in the F# worker |
|----------|-------------------------------|
| Happy Path | `AccountTransferWorkflow` runs Validate, Withdraw, Deposit, SendNotification |
| Advanced Visibility | Upserts the `Step` search attribute at each step |
| Human-in-the-Loop | Waits 30s for the `approveTransfer` signal or `approveTransferUpdate` update, or fails |
| API Downtime | Withdraw fails on attempts 1–4 and Temporal retries it until attempt 5 succeeds |
| Bug in Workflow | `failwith` after Withdraw fails the workflow *task*. Delete the line in `Workflows.fs` and restart the worker, and the same workflow completes |
| Invalid Account | Deposit fails with a non-retryable error, then UndoWithdraw runs and the workflow fails |
