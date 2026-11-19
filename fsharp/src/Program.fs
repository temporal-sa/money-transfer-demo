/// Entry point: connect to Temporal (local, or Cloud via API key or mTLS) and
/// run the worker until Ctrl-C.
module MoneyTransfer.Program

open System
open System.IO
open System.Threading
open Microsoft.Extensions.Logging
open Temporalio.Client
open Temporalio.Converters
open Temporalio.Worker
open MoneyTransfer.Model
open MoneyTransfer.EncryptionCodec

let private env name =
    match Environment.GetEnvironmentVariable name with
    | null
    | "" -> None
    | value -> Some value

let private envOr name defaultValue = env name |> Option.defaultValue defaultValue

/// How the worker authenticates to Temporal.
type Auth =
    | Local
    | ApiKey of string
    | MTls of cert: byte[] * key: byte[]

let private isLocal address =
    address = "localhost:7233" || address = "127.0.0.1:7233"

/// API key wins, then mTLS. A non-local address needs one of the two.
let parseAuth address : Result<Auth, string> =
    match env "TEMPORAL_API_KEY", env "TEMPORAL_CERT_PATH", env "TEMPORAL_KEY_PATH" with
    | Some apiKey, _, _ -> Ok(ApiKey apiKey)
    | None, Some certPath, Some keyPath -> Ok(MTls(File.ReadAllBytes certPath, File.ReadAllBytes keyPath))
    | _ when isLocal address -> Ok Local
    | _ ->
        Error
            $"Missing API key or mTLS cert for non local Temporal Address {address}: \
              set TEMPORAL_API_KEY, or TEMPORAL_CERT_PATH and TEMPORAL_KEY_PATH"

let private mask (secret: string) =
    if secret.Length <= 8 then "****" else $"{secret[..3]}...{secret[secret.Length - 4 ..]}"

let private connectOptions address ns auth encrypt =
    let options =
        TemporalClientConnectOptions(
            address,
            Namespace = ns,
            LoggerFactory =
                LoggerFactory.Create(fun builder ->
                    builder
                        .AddSimpleConsole(fun o -> o.TimestampFormat <- "[HH:mm:ss] ")
                        .SetMinimumLevel(LogLevel.Information)
                    |> ignore)
        )

    match auth with
    | Local -> ()
    | ApiKey apiKey ->
        printfn $"Using API Key: {mask apiKey}"
        options.ApiKey <- apiKey
        options.Tls <- TlsOptions()
        options.RpcMetadata <- dict [ "temporal-namespace", ns ] |> Collections.Generic.Dictionary
    | MTls(cert, key) ->
        printfn "setting TLS"
        options.Tls <- TlsOptions(ClientCert = cert, ClientPrivateKey = key)

    if encrypt then
        printfn "Encrypting payloads"
        let defaults = DataConverter.Default
        options.DataConverter <- DataConverter(defaults.PayloadConverter, defaults.FailureConverter, EncryptionCodec())

    options

let private runWorker taskQueue (options: TemporalClientConnectOptions) =
    task {
        let! client = TemporalClient.ConnectAsync options

        use cancel = new CancellationTokenSource()

        Console.CancelKeyPress.Add(fun e ->
            cancel.Cancel()
            e.Cancel <- true)

        let workerOptions =
            TemporalWorkerOptions(taskQueue)
                .AddAllActivities(Activities.moduleType, null)
                .AddWorkflow<AccountTransferWorkflow>()
                .AddWorkflow<AccountTransferWorkflowScenarios>()

        use worker = new TemporalWorker(client, workerOptions)
        printfn "Running worker..."

        try
            do! worker.ExecuteAsync(cancel.Token)
        with :? OperationCanceledException ->
            printfn "Worker cancelled"
    }

[<EntryPoint>]
let main _ =
    let address = envOr "TEMPORAL_ADDRESS" "127.0.0.1:7233"
    let ns = envOr "TEMPORAL_NAMESPACE" "default"
    let taskQueue = envOr "TEMPORAL_MONEYTRANSFER_TASKQUEUE" TaskQueue
    let encrypt = String.Equals(envOr "ENCRYPT_PAYLOADS" "", "true", StringComparison.OrdinalIgnoreCase)

    match parseAuth address with
    | Error message ->
        eprintfn $"{message}"
        1
    | Ok auth ->
        printfn $"Address is {address}"
        (runWorker taskQueue (connectOptions address ns auth encrypt)).GetAwaiter().GetResult()
        0
