# /// script
# requires-python = ">=3.10"
# ///
"""Builds docs/sell-sheet.html, the Java code walkthrough for the money-transfer demo, read through
Revedia's three use cases (EDI/OTC messages, reports, invoices and accruals). Every code panel is
regenerated with codeblock.py from the Java files as they are now. Run from the repo root after a code change:

  uv run --script docs/tools/sell_sheet.py

The generator and page design come from month-close-demo-java/docs/tools (2026-11-02), and the CSS is
pick-a-card-demo-python/walkthrough/template.html's (Pulsar, dark), read from there."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
J = "java/src/main/java/io/temporal/samples/moneytransfer"
TEMPLATE = Path.home() / "src/lab/pick-a-card-demo-python/walkthrough/template.html"


def rv(text: str) -> str:
    return f' <span class="rv">Revedia: {text}</span>'


# (file, codeblock.py arguments, notes as (number, text)); numbers run in page order across panels.
PANELS = {
    "workflow": (f"{J}/workflows/AccountTransferWorkflowImpl.java",
        ["--from", "public class AccountTransferWorkflowImpl", "--to", "return new TransferOutput",
         "--title", "AccountTransferWorkflowImpl.java",
         "--mark", "private final AccountTransferActivities withdrawActivities=1",
         "--mark", ".setStartToCloseTimeout(Duration.ofSeconds(5))=2",
         "--mark", ".setScheduleToCloseTimeout=3",
         "--mark", ".setRetryOptions(RetryOptions.newBuilder()=4",
         "--mark", "private final AccountTransferActivities depositActivities=5",
         "--mark", ".setHeartbeatTimeout(Duration.ofSeconds(5))=6",
         "--mark", "String idempotencyKey=7",
         "--mark", "activities.validate(input);=8",
         "--mark", "depositResponse = depositActivities.deposit(=9"],
        [(1, "<strong>Failure handling is configuration.</strong> Each step’s timeouts and retries are declared once, on the stub. There’s no try/catch, retry loop or sleep anywhere in the workflow."
             + rv("the same block wraps every call to SAP, the billing database or a partner’s endpoint.")),
         (2, "<strong>Per attempt:</strong> if the API hangs or the Worker dies mid-call, Temporal abandons that attempt after 5 s and tries again."),
         (3, "<strong>Overall budget:</strong> every retry together gets 5 minutes. This, not a count of attempts, bounds the retries."
             + rv("an SLA. Past it, the job fails visibly instead of silently.")),
         (4, "<strong>Back off:</strong> retry after 1 s, then 2, 4, 8 … up to 30 s between tries, so a struggling service gets room to recover. This is the API Downtime beat."
             + rv("a rolling deploy or a brief 503 between services delays a message, it doesn’t lose it.")),
         (5, "Deposit is the long step, so it gets its own options."),
         (6, "<strong>The hang detector.</strong> Deposit reports progress after every batch. If 5 s pass with no report, Temporal knows the Worker is gone or stuck, not just slow, and retries the step."
             + rv("a 3-day report that stalls is caught in seconds, not found on day 3.")),
         (7, "One idempotency key per transfer, generated inside the workflow so it’s the same on every retry and replay. Downstream systems use it to apply a retried call once."
             + rv("the key that stops a retried posting landing in SAP twice.")),
         (8, "<strong>Plain method calls, top to bottom.</strong> Each line is an Activity: Temporal records that it finished and retries it if it didn’t. A crash anywhere resumes at the next line, not the top. This is the Happy Path beat."
             + rv("an OTC response is the same shape: parse, validate, store, match it to what you sent, update the database, update the UI.")),
         (9, "The heartbeating deposit, called like any other step.")]),
    "deposit": (f"{J}/activities/AccountTransferActivitiesImpl.java",
        ["--range", "public DepositResponse deposit::return new DepositResponse",
         "--title", "AccountTransferActivitiesImpl.java (the deposit)", "--after", "9",
         "--mark", "throw ApplicationFailure.newNonRetryableFailure(=10",
         "--mark", "ctx.getHeartbeatDetails=11",
         "--mark", "simulateExternalOperation(1500);=12",
         "--mark", "ctx.heartbeat(batch);=13"],
        [(10, "<strong>Errors retrying can’t fix stop at once.</strong> A non-retryable failure ends the step on the first try; the workflow decides what happens next (note 18). This is the Invalid Account beat."
              + rv("SAP rejects an invoice, or an EDI message fails validation: no point retrying, so it goes to a person.")),
         (11, "<strong>The checkpoint.</strong> On a retry, the step reads its last heartbeat and carries on after the last batch it reported."),
         (12, "Your existing code goes here, unchanged. The loop around it is all the step adds."
              + rv("post a page of invoice lines, or build one country of a report.")),
         (13, "<strong>The heartbeat</strong> is both the progress you see in the Temporal UI (Last Heartbeat Details) and the checkpoint note 11 reads. It adds nothing to the workflow’s history. This is the Crash mid-Deposit beat."
              + rv("“country 4 of 10” on a long report, visible to support without opening a log.")),
         ]),
    "scenarios": (f"{J}/workflows/AccountTransferWorkflowScenarios.java",
        ["--range", "if (NEEDS_APPROVAL.equals(type)) {::// Withdraw",
         "--range", "if (BUG.equals(type)) {::throw new RuntimeException",
         "--range", "} catch (ActivityFailure e) {::throw ApplicationFailure.newNonRetryableFailure(message",
         "--range", "private void upsertStep::Workflow.upsertTypedSearchAttributes",
         "--range", "public void approveTransferSignal() {::approved = true;",
         "--title", "AccountTransferWorkflowScenarios.java (the parts the other beats use)", "--after", "13",
         "--mark", "Workflow.await(Duration.ofSeconds(approvalTime)=14",
         "--mark", "if (!receivedApproval)=15",
         "--mark", 'throw new RuntimeException("Simulated bug=16',
         "--mark", "activities.undoWithdraw=17",
         "--mark", "throw ApplicationFailure.newNonRetryableFailure(message=18",
         "--mark", "Workflow.upsertTypedSearchAttributes=19",
         "--mark", "approved = true;=20"],
        [(14, "<strong>A wait for a person, in one line.</strong> The workflow holds here until approval arrives or the window closes, whether that’s seconds or days. Waiting holds no Worker and no thread. This is the Human in the Loop beat."
              + rv("finance approves the close before invoices go out; an accrual waits weeks for the distributor’s late statement.")),
         (15, "No approval in time is just a branch: fail with a reason, and it shows up in search."
              + rv("a statement that never arrives is flagged, not forgotten.")),
         (16, "<strong>The bug.</strong> A code bug fails the workflow <em>task</em>, not the workflow: the transfer stays Running and keeps retrying, with the money safe after the withdraw. Fix the code, restart the Workers, and the stuck transfers finish on their own. This is the Bug in Workflow beat."
              + rv("a wrong per-organization EDI rule: fix it and the stuck messages complete, with no manual replay or cleanup.")),
         (17, "<strong>Compensation.</strong> The deposit failed for good, so put the withdrawal back. A saga is a try/catch."
              + rv("undo a partial posting instead of leaving a half-written record and a wrong status.")),
         (18, "Then fail the transfer with the original reason, readable in the UI."),
         (19, "<strong>Search labels.</strong> The workflow records its current step as a Search Attribute, so you can list every transfer by where it is: <code>Step = 'Deposit'</code>. In this Java version only the Advanced Visibility scenario sets it."
              + rv("“every invoice waiting on SAP”, or “every report that failed last night”: Thearon’s to-do list on login.")),
         (20, "<strong>The Signal.</strong> Approval arrives as a message to the running workflow. The Update version (not shown) also validates first and replies to the caller."
              + rv("an inbound webhook, such as SAP’s acknowledgement or a partner’s EDI response, becomes a Signal to the job waiting for it."))]),
    "worker": (f"{J}/AccountTransferWorker.java",
        ["--range", "WorkerFactory factory::factory.start();", "--title", "AccountTransferWorker.java", "--after", "20",
         "--mark", "Worker worker = factory.newWorker=21", "--mark", ".setMaxHeartbeatThrottleInterval=22"],
        [(21, "<strong>The Worker is an ordinary process.</strong> It runs your code and polls Temporal for work; Temporal keeps each workflow’s state. Run it as a Spring Boot service on AKS and scale it like any other."
              + rv("redeploying it mid-message is safe: in-flight work carries on from its last step.")),
         (22, "The SDK holds heartbeats back to save calls. For the demo it sends each one within a second, so the UI always shows the latest batch. In production, keep the default.")]),
}


def panel(name: str) -> str:
    file, args, _ = PANELS[name]
    run = subprocess.run(["uv", "run", "--script", str(DOCS / "tools/codeblock.py"), file, *args], cwd=ROOT,
                         capture_output=True, text=True)
    if run.returncode:
        sys.exit(f"codeblock.py failed for {name}: {run.stderr}")
    return run.stdout


def diagram() -> str:
    """The four steps as one static SVG (no script): step boxes, what each means for Revedia, and the
    Temporal Service recording every step underneath."""
    steps = [("1", "Validate", "OTC: parse and check the message", "SAP: is the document known?"),
             ("2", "Withdraw", "OTC: store it, match the reply", "SAP: post the payment, once"),
             ("3", "Deposit", "Report: one country at a time", "Heartbeat after each batch"),
             ("4", "Notify", "Tell the customer or the UI", "Update the database")]
    bw, gap, x0, y0 = 320, 44, 24, 24
    out = []
    for i, (n, name, l1, l2) in enumerate(steps):
        x = x0 + i * (bw + gap)
        hb = name == "Deposit"
        stroke = "var(--green)" if hb else "var(--uv)"
        out.append(f'<g><title>{name}: {l1}; {l2}</title>'
                   f'<rect x="{x}" y="{y0}" width="{bw}" height="140" rx="6" fill="var(--panel)" stroke="{stroke}" stroke-width="1.5"/>'
                   f'<text x="{x+16}" y="{y0+30}" font-family="var(--mono)" font-size="13" fill="var(--lilac)">STEP {n}</text>'
                   f'<text x="{x+16}" y="{y0+58}" font-family="var(--sans)" font-size="26" font-weight="600" fill="var(--fg)">{name}</text>'
                   f'<text x="{x+16}" y="{y0+92}" font-family="var(--sans)" font-size="16" fill="#7fd4ff">{l1}</text>'
                   f'<text x="{x+16}" y="{y0+118}" font-family="var(--sans)" font-size="16" fill="#7fd4ff">{l2}</text></g>')
        if i < 3:
            ax = x + bw
            out.append(f'<line x1="{ax+4}" y1="{y0+66}" x2="{ax+gap-8}" y2="{y0+66}" stroke="var(--muted)" stroke-width="1.5"/>'
                       f'<path d="M{ax+gap-8} {y0+60} l8 6 l-8 6z" fill="var(--muted)"/>')
    w = x0 * 2 + 4 * bw + 3 * gap
    by = y0 + 140 + 22
    out.append(f'<g><title>Every step is recorded by the Temporal Service, so a crash resumes at the next step</title>'
               f'<rect x="{x0}" y="{by}" width="{w - 2*x0}" height="46" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>'
               f'<text x="{w/2}" y="{by+30}" text-anchor="middle" font-family="var(--sans)" font-size="17" fill="var(--fg)">'
               f'The Temporal Service records each step. A crash, a redeploy or an outage resumes at the next step, not the top.</text></g>')
    h = by + 46 + 20
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="Four steps in order: validate, withdraw, deposit, notify, '
            f'recorded by the Temporal Service" style="display:block">' + "".join(out) + "</svg>")


def walk(name: str) -> str:
    notes = "".join(f'        <li><span class="n">{n}</span><span>{t}</span></li>\n' for n, t in PANELS[name][2])
    return f'<div class="walk">\n      {panel(name)}\n      <ol class="notes">\n{notes}      </ol>\n    </div>'


def main() -> None:
    tpl = TEMPLATE.read_text()
    css = tpl[tpl.index("<style>"):tpl.index("</style>")] + """
/* Java tokens (Pygments), in the same Pulsar palette */
.tok-kd, .tok-kt, .tok-kr { color: #a5abff; }
.tok-nc, .tok-nf { color: var(--fg); }
.tok-na { color: #7fd4ff; }
.rv { display: block; margin-top: 6px; color: #7fd4ff; }
.map td:first-child { white-space: nowrap; }
/* Wider than the template, so Java's long lines wrap less: the code gets ~70% of a 96rem page */
.page { max-width: 96rem; }
.walk { grid-template-columns: minmax(0, 7fr) minmax(0, 3fr); }
@media (max-width: 760px) { .walk { grid-template-columns: minmax(0, 1fr); } }
header .lede, .sec-head p { max-width: 64rem; }
"""
    lines = sum(len((ROOT / J / f).read_text().splitlines()) for f in
                ["workflows/AccountTransferWorkflowImpl.java", "activities/AccountTransferActivitiesImpl.java"])
    page = f"""<meta charset="utf-8">
<title>Money transfer, read as Revedia</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Noto+Sans+Mono:wght@400;600&display=swap">
{css}</style>

<main class="page">
  <header>
    <div class="eyebrow">Java SDK · Code walkthrough</div>
    <h1>The money-transfer demo, read as Revedia’s workloads</h1>
    <p class="lede">This is Temporal’s standard demo, not a Revedia build. Watch the shape rather than the domain. A transfer is four steps in order (validate, withdraw, deposit, notify), each calling a system that can fail. That’s also an OTC response, an invoice posted to SAP, and a report working through its countries. The workflow and its steps are {lines} lines of plain Java; every line in <span class="rv" style="display:inline">blue</span> says what a step means for Revedia.</p>
  </header>

  <section>
    <div class="sec-head">
      <div class="eyebrow">The shape</div>
      <h2>Four steps, recorded as they run</h2>
    </div>
    <div class="table-wrap" style="padding:8px 0">
      {diagram()}
    </div>
  </section>

  <section>
    <div class="sec-head">
      <div class="eyebrow">How to read it</div>
      <h2>Wherever you see “transfer”, picture one of yours</h2>
    </div>
    <div class="table-wrap">
      <table class="map">
        <thead><tr><th>Revedia workload</th><th>The same shape in this demo</th><th>Beats that show it</th></tr></thead>
        <tbody>
          <tr><td>EDI / OTC message processing</td><td>Each inbound message is one workflow: parse, validate, store, match it to what you sent, update the database, update the UI. Retries survive rolling deploys; a bad message fails fast to a person; the partner’s response arrives as a Signal.</td><td>Happy Path, API Downtime, Invalid Account, Bug in Workflow (notes 1–4, 8, 10, 16, 20)</td></tr>
          <tr><td>Report generation, scheduled and ad hoc</td><td>A long report is the heartbeating deposit: it reports progress after each chunk, a dead or hung Worker is caught in seconds, and the retry carries on from the last checkpoint. Scheduled reports are a Temporal Schedule (the notebook’s standing order); ad hoc ones are the same workflow started from the UI.</td><td>Crash mid-Deposit, Schedules (notes 6, 11–13)</td></tr>
          <tr><td>Invoice and accrual generation</td><td>An invoice is a posting to SAP, made exactly once with an idempotency key, rolled back if it can’t complete. The close waits for finance’s approval; an accrual waits weeks for a late statement. Each is findable by its own labels.</td><td>Human in the Loop, Invalid Account, Search (notes 7, 14, 15, 17, 19)</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <section>
    <div class="sec-head">
      <div class="eyebrow">AccountTransferWorkflowImpl.java</div>
      <h2>The transfer, as code</h2>
      <p>Read it top to bottom: the process, in order. The failure handling is all in the options at the top.</p>
    </div>
    {walk("workflow")}
  </section>

  <section>
    <div class="sec-head">
      <div class="eyebrow">AccountTransferActivitiesImpl.java</div>
      <h2>The long step: report progress, resume from it</h2>
      <p>The deposit posts in six batches and checks in with Temporal after each. Kill the Worker after batch 2 and the restarted Worker logs <code>Deposit resuming after batch 2 of 6</code>, then posts 3 to 6.</p>
    </div>
    {walk("deposit")}
  </section>

  <section>
    <div class="sec-head">
      <div class="eyebrow">AccountTransferWorkflowScenarios.java</div>
      <h2>Waiting for a person, recovering from a bug, undoing a step</h2>
      <p>One workflow plays every scenario in the demo, picked by its type. These are the lines each beat relies on.</p>
    </div>
    {walk("scenarios")}
  </section>

  <section>
    <div class="sec-head">
      <div class="eyebrow">Running it</div>
      <h2>The Worker</h2>
    </div>
    {walk("worker")}
  </section>

  <div class="src">
    <span>Sources, docs.temporal.io:</span>
    <span>/encyclopedia/retry-policies · /encyclopedia/detecting-activity-failures (timeouts, heartbeat timeout)</span>
    <span>/design-patterns/long-running-activity (heartbeat checkpoints) · /design-patterns/approval (wait with a timeout)</span>
    <span>/handling-messages (Signals, Updates) · /develop/java/platform/observability (Search Attributes)</span>
  </div>
</main>
"""
    (DOCS / "sell-sheet.html").write_text(page)
    print(f"wrote docs/sell-sheet.html ({lines} lines of workflow and activity code quoted from the source)")


if __name__ == "__main__":
    main()
