"""Write the transfer's story into the Temporal UI.

Always on: worker.py registers it. Nothing in the workflows changes: this interceptor
adds a summary to every Activity (real amounts, accounts and idempotency key) and keeps the
workflow's Current Details as a status card: what it is doing now, and each step's state.
It is rewritten at every step, not appended to: the Event History is already the log.
Summaries and details are payloads, so with ENCRYPT_PAYLOADS=true they are encrypted too.
"""

from __future__ import annotations

from typing import Any, Optional

from temporalio import workflow
from temporalio.common import RawValue
from temporalio.worker import (
    ExecuteWorkflowInput,
    HandleSignalInput,
    HandleUpdateInput,
    Interceptor,
    StartActivityInput,
    WorkflowInboundInterceptor,
    WorkflowInterceptorClassInput,
    WorkflowOutboundInterceptor,
)

with workflow.unsafe.imports_passed_through():
    from shared_objects import TransferInput


class NarrativeInterceptor(Interceptor):
    def workflow_interceptor_class(
        self, input: WorkflowInterceptorClassInput
    ) -> Optional[type[WorkflowInboundInterceptor]]:
        return _Inbound


class _Story:
    """The transfer and its status card, rendered as the workflow's Current Details."""

    NAMES = {"validate": "Validate", "withdraw": "Withdraw", "deposit": "Deposit",
             "sendNotification": "Notify", "undoWithdraw": "Undo withdraw"}

    def __init__(self) -> None:
        self.transfer: Optional[TransferInput] = None
        self.steps: dict[str, str] = {}  # step name -> mark, in the order the steps happened
        self.now = ""

    def step(self, name: str, mark: str, now: str) -> None:
        self.steps[self.NAMES.get(name, name)] = mark
        self.update(now)

    def update(self, now: str) -> None:
        self.now = now
        steps = "  ".join(f"{mark} {name}" for name, mark in self.steps.items())
        workflow.set_current_details(f"**Now:** {now}\n\n{steps}")


def _transfer(args: Any) -> Optional[TransferInput]:
    for a in args:
        if hasattr(a, "fromAccount"):  # the sandbox loads its own copy of TransferInput, so no isinstance
            return a
        if isinstance(a, RawValue):  # the scenarios workflow is dynamic, so its input arrives raw
            return workflow.payload_converter().from_payload(a.payload, TransferInput)
        if isinstance(a, (list, tuple)):
            found = _transfer(a)
            if found:
                return found
    return None


class _Inbound(WorkflowInboundInterceptor):
    def init(self, outbound: WorkflowOutboundInterceptor) -> None:
        self.story = _Story()
        super().init(_Outbound(outbound, self.story))

    async def execute_workflow(self, input: ExecuteWorkflowInput) -> Any:
        self.story.transfer = _transfer(input.args)
        self.story.update("Starting")
        try:
            result = await super().execute_workflow(input)
        except Exception as e:
            kind, msg = getattr(e, "type", None) or type(e).__name__, str(e).strip()
            self.story.update(f"❌ Failed: {msg if msg.startswith(kind) else f'{kind}: {msg}'}")
            raise
        self.story.update("✅ Done")
        return result

    async def handle_signal(self, input: HandleSignalInput) -> None:
        await super().handle_signal(input)
        if input.signal == "approveTransfer":
            self.story.step("Approved", "👤", "👤 Approved by a person (Signal)")

    async def handle_update_handler(self, input: HandleUpdateInput) -> Any:
        result = await super().handle_update_handler(input)
        self.story.step("Approved", "👤", "👤 Approved by a person (Update)")
        return result


class _Outbound(WorkflowOutboundInterceptor):
    def __init__(self, next: WorkflowOutboundInterceptor, story: _Story) -> None:
        super().__init__(next)
        self.story = story

    def start_activity(self, input: StartActivityInput) -> workflow.ActivityHandle:
        summary = self._summary(input.activity, input.args)
        input.summary = input.summary or summary
        self.story.step(input.activity, "⏳", f"⏳ {summary}")
        handle = super().start_activity(input)
        handle.add_done_callback(lambda h: self._done(h, input.activity))
        return handle

    def _done(self, handle: workflow.ActivityHandle, name: str) -> None:
        step = _Story.NAMES.get(name, name)
        if handle.cancelled():
            self.story.step(name, "⚠️", f"⚠️ {step} cancelled")
        elif handle.exception():
            self.story.step(name, "❌", f"❌ {step} failed: {handle.exception().cause or handle.exception()}")
        else:
            self.story.step(name, "✔️", f"✔️ {step} done")

    def _summary(self, name: str, args: Any) -> str:
        t = self.story.transfer
        frm, to = (t.fromAccount, t.toAccount) if t else ("?", "?")
        if name == "validate":
            return f"Validate ${t.amount:,} from {frm} to {to}" if t else "Validate the transfer"
        if name == "withdraw":
            return f"Withdraw ${args[1]:,} from {frm} · idempotency key {args[0][:8]}"
        if name == "deposit":
            return f"Deposit ${args[1]:,} into {to} · idempotency key {args[0][:8]}"
        if name == "sendNotification":
            return f"Notify {frm} and {to} that ${t.amount:,} moved" if t else "Send the notification"
        if name == "undoWithdraw":
            return f"Compensate: return ${args[0]:,} to {frm} because the deposit failed"
        return name
