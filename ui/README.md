# Money Transfer Web

Demos various aspects of [Temporal](https://temporal.io).

![UI Screenshot](./ui.png)

## Configuration

The sample is configured by default to connect to
a [local Temporal Server](https://docs.temporal.io/cli#starting-the-temporal-server) running on localhost:7233.

To instead connect to Temporal Cloud, set the following environment variables, replacing them with your own Temporal
Cloud credentials:

```bash
TEMPORAL_ADDRESS=testnamespace.sdvdw.tmprl.cloud:7233
TEMPORAL_NAMESPACE=testnamespace.sdvdw
TEMPORAL_CERT_PATH="/path/to/file.pem"
TEMPORAL_KEY_PATH="/path/to/file.key"
````

(optional) set a task queue name

```bash
export TEMPORAL_MONEYTRANSFER_TASKQUEUE="MoneyTransfer"
```

## Run a Workflow

Run the Money Transfer Web UI:

```bash
ENCRYPT_PAYLOADS=true ./gradlew run --console=plain
```

Then navigate to `http://localhost:7070/`

## Demo various failures and recoveries

A dropdown menu simulates the following scenarios

#### Happy Path

- The transfer will run to completion, and is crash-proof

#### Advanced Visibility

The transfer will in addition to running to completion, upsert a search attribute called Step. The Step search attribute
defines what part of the workflow is being executed: withdraw or deposit. By upserting a search attribute we are able to
search workflows by not only execution status, time, duration but also, based on business logic exposed by the search
attribute.

In order to demonstrate this feature the [search attribute](https://docs.temporal.io/visibility#search-attribute)
```Step``` which is a ```Keyword``` must be created in the Temporal namespace. This can be accomplished using the UI or
CLI.

#### Require Human-In-Loop Approval

The transfer will pause and wait for approval. If the user doesn't approve the transfer within a set time, the workflow
will fail.

Approve a transfer using **Signals**

```bash
temporal workflow signal \
 --env prod \
 --query 'WorkflowId="TRANSFER-XXX-XXX"' \
 --name approveTransfer \
 --reason 'approving transfer'
```

Approve a transfer using **Updates**

```bash
temporal workflow update \
 --env prod \
 --workflow-id TRANSFER-XXX-XXX \
 --name approveTransferUpdate
```

The workflow's Update function has a [validator](https://docs.temporal.io/dev-guide/java/features#validate-an-update).
It will reject an Update if:

- The transfer isn't waiting for approval
- The transfer has already been approved

#### Simulate a Bug in the Workflow (recoverable failure)

Comment out the RuntimeException in the workflow code (`AccountTransferWorkflowImpl.java`) and restart the worker to fix
the 'bug'.

#### Simulate API Downtime (recover on 5th attempt)

Will introduce artifical delays in the `withdraw` activity's API calls. This will cause activity retries. After 5
retries, the delay will be removed and the workflow will proceed.

#### Invalid Account (unrecoverable failure)

Introduces an unrecoverable failure in the `deposit` activity (invalid account). The workflow will fail after running
compensation activities (`undoWithdraw`).

#### Schedule a recurring transfer

Creates a [Schedule](https://docs.temporal.io/workflows#schedule) that will run a set of workflows on a cadence.

Produces a schedule ID, which you can inspect in the Temporal UI's "Schedules" menu.

## Advanced: Reset workflows

#### List failed workflows

temporal workflow list --env prod -q 'ExecutionStatus="Failed" OR ExecutionStatus="Terminated"'

## Enable Encryption

Remove the `ENCRYPT_PAYLOADS` variable in each command to run without encryption.

You can decrypt these payloads in Temporal Cloud's UI/cli using the codec server:
`https://codec.tmprl-demo.cloud` ([source](https://github.com/steveandroulakis/temporal-codec-server)). Ensure you
switch on "Pass the user access token with your endpoint". Note: The codec server is only compatible with workflows
running in Temporal Cloud.

---

## Where is the UI code?

The page is a [SvelteKit](https://kit.svelte.dev/) app in [`web/`](web). The Java server serves its static build
from `src/main/resources/svelte_ui`, which is committed so the UI runs without Node.

To change the UI, edit `web/src/routes/+page.svelte`, then rebuild and commit the output with your change:

```bash
cd web
npm ci
npm run build   # writes ../src/main/resources/svelte_ui
```

The source was recovered from
[temporal-money-transfer-typescript](https://github.com/temporal-sa/temporal-money-transfer-typescript), with the
Advanced Visibility scenario added back to match the bundle that shipped here.
