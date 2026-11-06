from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio import workflow

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

        # Withdraw
        await workflow.execute_activity(
            AccountTransferActivities.withdraw,
            args=[idempotencyKey, input.amount, workflow_type],
            start_to_close_timeout=self.start_to_close_timeout,
            retry_policy=self.retry_policy,
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
        await self.updateProgress(100, 0, "finished")

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
