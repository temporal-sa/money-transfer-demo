# F# with the Temporal .NET SDK: pitfalls

The Temporal .NET SDK (`Temporalio`) is written for C#, but it works well from F#. This
page lists what is *specific to F#*. General Temporal and .NET SDK guidance (determinism,
retries, signals and updates, testing) applies to F# unchanged and isn't repeated here.

Checked against Temporalio 1.14.0 on .NET 9.

- [1. Async in workflow code](#1-async-in-workflow-code)
- [2. Calling the SDK from F#](#2-calling-the-sdk-from-f)
- [3. Workflow classes and state](#3-workflow-classes-and-state)
- [4. Exceptions](#4-exceptions)

## 1. Async in workflow code

The SDK runs workflow code on its own deterministic task scheduler. F# has two ways to
write asynchronous code, and only one of them stays on that scheduler.

### Use `task { }`, never `async { }`

`task { }` resumes after each `let!`/`do!` on the current scheduler, just like C#
`await`, so it stays on the workflow scheduler. F#'s `Async` runs its own timers and
thread switches outside it.

```fsharp
// Good
task {
    do! Workflow.DelayAsync(TimeSpan.FromSeconds 1.0)
}

// Bad: the workflow hangs, with no error anywhere
task {
    do! async { do! Async.Sleep 1000 } |> Async.StartAsTask
}
```

### The SDK's safety net doesn't catch F# `Async`

By default the SDK fails the workflow *task* when workflow code leaves the workflow
scheduler, so the problem shows up in the UI with an error and can be fixed and
redeployed. That check catches .NET `Task` escapes, but **not F# `Async`**. Results of
running each of these inside a workflow:

| In workflow code | Result | Caught? |
|---|---|---|
| `Task.Run`, `Task.Delay` (for comparison) | Workflow task fails with a clear error | Yes |
| `backgroundTask { }` | Workflow task fails: "not scheduled on workflow scheduler" | Yes |
| `async { do! Async.Sleep .. }` started with `Async.StartAsTask` | Workflow hangs as Running, with no error in history or logs | **No** |
| `Async.RunSynchronously` | Blocks the workflow thread. Short calls complete; long ones should trip the SDK's deadlock detection (about 2s) | Partly |

A silent hang is the worst outcome, because nothing points at the cause. When reviewing
F# workflow code, search for:

```
async {    Async.Sleep    Async.Start    Async.Parallel    Async.SwitchTo    Async.RunSynchronously    backgroundTask
```

### Wrapping SDK calls in `async` happened to work

A team with an existing `async`-based codebase may wrap SDK calls rather than rewrite
them. This completed and replayed correctly in testing:

```fsharp
async { do! Async.AwaitTask(Workflow.DelayAsync(TimeSpan.FromSeconds 1.0)) }
|> Async.StartImmediateAsTask
```

So did wrapping `Workflow.ExecuteActivityAsync`, and a 1,000-step `async` chain followed
by an SDK call. This works only because of how FSharp.Core currently runs those
continuations, not because anything guarantees it. Prefer `task { }`. If you keep a
wrapper layer, cover it with replay tests and keep `Async.Sleep`, `Async.Parallel` and
similar out of it.

### Third-party computation expressions

Libraries such as TaskSeq and IcedTasks schedule work in their own ways. Test them with
replay before using them in workflow code.

### Activities are not affected

These rules apply only to workflow code. Activities can use `async { }`, `Async.Sleep`
and anything else.

## 2. Calling the SDK from F#

### Give activity calls an explicit result type

`Workflow.ExecuteActivityAsync` has many overloads. With an F# lambda, the compiler can't
choose between them and reports error FS0041. Give the result type explicitly:

```fsharp
// FS0041: ambiguous overload
Workflow.ExecuteActivityAsync((fun () -> MyActivities.charge input), options)

// Works
Workflow.ExecuteActivityAsync<string>((fun () -> MyActivities.charge input), options)
```

The lambda is turned into a LINQ expression that the SDK reads to find the activity's
name and arguments; it is never called in the workflow. F# only converts a lambda to an
expression at a method call, so you can't build one in a `let` and pass it in later. For
a reusable helper, write a static member that takes an `Expression<Func<...>>`:

```fsharp
type Act =
    static member Run<'T>(call: Expression<Func<Task<'T>>>) =
        Workflow.ExecuteActivityAsync<'T>(call, options)
```

### Activities can be module functions

Activities don't need a class. Put `[<Activity>]` on functions in a module and register
the module's type:

```fsharp
module MyActivities =
    type private Marker = class end
    let moduleType = nonNull typeof<Marker>.DeclaringType

    [<Activity("Charge")>]
    let charge (input: ChargeInput) : Task<string> = task { return "ok" }

// in the worker
TemporalWorkerOptions(taskQueue).AddAllActivities(MyActivities.moduleType, null)
```

- `nonNull` is needed because `DeclaringType` is nullable when the project has
  `<Nullable>enable</Nullable>`.
- Name activities explicitly (`[<Activity("Charge")>]`). Otherwise the name comes from
  the F# function name (`charge`), which won't match C#-style names (`Charge`) used by
  workflows or workers written in other languages.

### JSON: records and options work, unions don't

The default payload converter (System.Text.Json) handles F# records, `option` (as the
value or `null`) and lists with no extra setup. **Discriminated unions throw
`NotSupportedException`.** Either keep unions out of payloads (map them to a string or a
record at the boundary), or add a converter such as FSharp.SystemTextJson to the
data converter.

F# field names are serialized as written (`Amount`, not `amount`). If code in another
language reads or writes the payload, pin the names:

```fsharp
type ChargeInput =
    { [<JsonPropertyName "amount">] Amount: int
      [<JsonPropertyName "accountId">] AccountId: string }
```

### SDK option types are C# records

Some SDK types, such as `DataConverter`, are C# records. F#'s `{ x with ... }` syntax
only works on F# records, so build a new one through its constructor instead:

```fsharp
let defaults = DataConverter.Default
DataConverter(defaults.PayloadConverter, defaults.FailureConverter, MyCodec())
```

### Use `nameof` for update validators

`[<WorkflowUpdateValidator>]` takes the update *method's* name. A string literal goes
stale if the method is renamed, so use `nameof`:

```fsharp
[<WorkflowUpdateValidator(nameof Unchecked.defaultof<MyWorkflow>.Approve)>]
member _.ValidateApprove() : unit = ...
```

## 3. Workflow classes and state

### The workflow has to be a class

The SDK finds workflows, queries, signals and updates through attributes on a class,
and handlers need to share state with the running workflow. Keep the class thin: put
domain logic in records, unions and functions, and keep only the state and the
SDK-facing members in the class.

### `let mutable` fields need no locks

Queries, signals and updates run on the same single workflow thread as the main code,
and only while it is paused at a `let!`/`do!`. So a `let mutable` field in the workflow
class needs no locks.

### Module-level helpers that call `Workflow.*`

F# encourages pulling logic into module functions. That's fine, but a function that
calls `Workflow.Random`, `Workflow.UtcNow` or `Workflow.DelayAsync` works only when called
from workflow code. Called from an activity or a unit test, it throws.

## 4. Exceptions

F#'s built-in helpers (`failwith`, `invalidOp`, `invalidArg`) throw ordinary .NET
exceptions. In **workflow** code, an ordinary exception does *not* fail the workflow: it
fails the workflow *task*, which then retries until you fix and redeploy the code. That
is useful for bugs, but surprising if you meant to end the workflow.

```fsharp
// Pauses the workflow until the code is fixed
failwith "Account is invalid"

// Fails the workflow
raise (ApplicationFailureException "Account is invalid")
```

Use `ApplicationFailureException` whenever a workflow should fail for a business reason.
