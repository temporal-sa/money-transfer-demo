from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from activities import AccountTransferActivities
from shared_objects import (
    DepositResponse,
    TransferInput,
    TransferOutput,
    TransferStatus,
)


@workflow.defn
class AccountTransferWorkflow:
    def __init__(self) -> None:
        self.progress = 0
        self.transferState = ""
        self.depositResponse = DepositResponse("")
        self.start_to_close_timeout = timedelta(seconds=5)
        self.retry_policy = AccountTransferActivities.retry_policy

    @workflow.run
    async def transfer(self, input: TransferInput) -> TransferOutput:
        workflow_type = workflow.info().workflow_type
        logger = workflow.logger
        logger.info(f"Simple workflow started {workflow_type}, input = {input}")
        idempotencyKey = str(workflow.uuid4())

        # Validate
        await workflow.execute_activity(
            AccountTransferActivities.validate,
            args=[input],
            start_to_close_timeout=self.start_to_close_timeout,
            retry_policy=self.retry_policy,
        )
        await self.updateProgress(25, 1)

        # Withdraw, with every failure-handling option spelled out. All of it is declarative:
        # no try/except, no retry loop, no sleep. The other three calls get the same behaviour from defaults.
        await workflow.execute_activity(
            AccountTransferActivities.withdraw,
            args=[idempotencyKey, input.amount, workflow_type],
            # Time to complete, per attempt: if the bank API hangs or the worker dies mid-call,
            # Temporal gives up on this attempt after 5s and retries it. Always set this one.
            start_to_close_timeout=timedelta(seconds=5),
            # Time to complete, overall: the whole withdrawal, every retry included, gets 5 minutes.
            # This, not a count of attempts, is what bounds the retries below.
            schedule_to_close_timeout=timedelta(minutes=5),
            # Time to start: how long the task may wait in the queue for a worker. Off on purpose:
            # it is never retried, so a worker outage longer than this would fail the transfer.
            # schedule_to_start_timeout=timedelta(minutes=1),
            # Heartbeats: for long-running work that reports progress, so a lost worker is noticed early.
            # A withdrawal takes a second, so it doesn't heartbeat.
            # heartbeat_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),  # first retry after 1s
                backoff_coefficient=2.0,                # then 2s, 4s, 8s ... backing off the struggling API
                maximum_interval=timedelta(seconds=30), # but never wait more than 30s between tries
                maximum_attempts=0,                     # 0 = unlimited; the 5-minute budget is the limit
                # Errors that retrying can't fix stop at once, e.g. non_retryable_error_types=["InsufficientFunds"].
                # Deposit does the same from the other side: it raises InvalidAccount with non_retryable=True.
            ),
        )
        await self.updateProgress(50, 3)

        # Deposit
        self.depositResponse = await workflow.execute_activity(
            AccountTransferActivities.deposit,
            args=[idempotencyKey, input.amount, workflow_type],
            start_to_close_timeout=self.start_to_close_timeout,
            retry_policy=self.retry_policy,
        )
        await self.updateProgress(75, 1)

        # Send Notification
        await workflow.execute_activity(
            AccountTransferActivities.sendNotification,
            args=[input],
            start_to_close_timeout=self.start_to_close_timeout,
            retry_policy=self.retry_policy,
        )
        await self.updateProgress(100, 1, "finished")

        return TransferOutput(DepositResponse(self.depositResponse.get_chargeId()))

    @workflow.query(name="transferStatus")
    def queryTransferStatus(self) -> TransferStatus:
        return TransferStatus(
            self.progress, self.transferState, "", self.depositResponse, 0
        )

    async def updateProgress(
        self, progress: int, sleep: int, transferState: Optional[str] = "running"
    ) -> None:
        if sleep > 0:
            await asyncio.sleep(sleep)

        self.transferState = transferState
        self.progress = progress
