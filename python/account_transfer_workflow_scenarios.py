import asyncio
from collections.abc import Sequence
from typing import Any

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RawValue, SearchAttributeKey
from temporalio.exceptions import ApplicationError

from shared_objects import TransferInput, TransferOutput, TransferStatus, DepositResponse
from activities import AccountTransferActivities

@workflow.defn(dynamic=True)
class AccountTransferWorkflowScenarios:

    BUG = "AccountTransferWorkflowRecoverableFailure"
    NEEDS_APPROVAL = "AccountTransferWorkflowHumanInLoop"
    ADVANCED_VISIBILITY = "AccountTransferWorkflowAdvancedVisibility"

    WORKFLOW_STEP = SearchAttributeKey.for_keyword("Step")

    approvalTime = 30
    approved = False

    def __init__(self) -> None:
        self.progress = 0
        self.transferState = ""
        self.depositResponse = DepositResponse("")
        self.start_to_close_timeout = timedelta(seconds=5)
        self.retry_policy = AccountTransferActivities.retry_policy

    @workflow.run
    async def execute(self, args: Sequence[RawValue]) -> Any:
        input = workflow.payload_converter().from_payload(args[0].payload, TransferInput)
        self.workflow_type = workflow.info().workflow_type
        logger = workflow.logger
        logger.info(f"Dynamic Account Transfer Workflow started {self.workflow_type}, input = {input}")
        idempotencyKey = str(workflow.uuid4())

        # Validate
        self.upsertStep("Validate")
        await workflow.execute_activity(AccountTransferActivities.validate,
            args=[input],
            start_to_close_timeout=self.start_to_close_timeout,
            retry_policy=self.retry_policy)
        await self.updateProgress(25, 1)

        if self.NEEDS_APPROVAL == self.workflow_type:
            logger.info(f"Waiting on 'approveTransfer' Signal or Update for workflow ID: {workflow.info().workflow_id}")
            await self.updateProgressStatus(30, 0, "waiting")

            # Wait for approval for up to approvalTime
            try:
                await workflow.wait_condition(lambda: self.approved, timeout=timedelta(seconds=self.approvalTime))
            except asyncio.TimeoutError:
                logger.error(f"Approval not received within the {self.approvalTime} seconds")
                raise ApplicationError(f"Approval not received within {self.approvalTime} seconds", type="ApprovalTimeout", non_retryable=True)

        # Withdraw
        self.upsertStep("Withdraw")
        await workflow.execute_activity(AccountTransferActivities.withdraw,
            args=[idempotencyKey, input.amount, self.workflow_type],
            start_to_close_timeout=self.start_to_close_timeout,
            retry_policy=self.retry_policy)
        await self.updateProgress(50, 3)

        if self.BUG == self.workflow_type:
            # simulate bug
            raise RuntimeError("Simulated bug - fix me!")

        # Deposit
        self.upsertStep("Deposit")
        try:
            self.depositResponse = await workflow.execute_activity(AccountTransferActivities.deposit,
                args=[idempotencyKey, input.amount, self.workflow_type],
                start_to_close_timeout=self.start_to_close_timeout,
                retry_policy=self.retry_policy)
            await self.updateProgress(75, 1)
        except Exception as ex:
            logger.info(f"Depsoit failed unrecoverable error, reverting withdraw")
            # Undo Withdraw (rollback)
            await workflow.execute_activity(AccountTransferActivities.undoWithdraw,
                args=[input.amount],
                start_to_close_timeout=self.start_to_close_timeout,
                retry_policy=self.retry_policy)

            # return failure message
            raise ApplicationError(f"{ex.__cause__} ", type="DepositFailed", non_retryable=True)

        # Send Notification
        self.upsertStep("Send notification")
        await workflow.execute_activity(AccountTransferActivities.sendNotification,
            args=[input],
            start_to_close_timeout=self.start_to_close_timeout,
            retry_policy=self.retry_policy)
        await self.updateProgressStatus(100, 1, "finished")

        return TransferOutput(DepositResponse(self.depositResponse.get_chargeId()))

    @workflow.signal(name="approveTransfer")
    def approveTransferSignal(self) -> str:
        workflow.logger.info(f"Approve Signal Received")
        if self.transferState == "waiting":
            self.approved = True
        else:
            workflow.logger.info(f"Approval not applied. Transfer is not waiting for approval")

    @workflow.update(name="approveTransferUpdate")
    def approveTransferUpdate(self) -> str:
        workflow.logger.info(f"Approve Update Validated: Approving Transfer")
        self.approved = True
        return "successfully approved transfer"

    @approveTransferUpdate.validator
    def approveTransferUpdateValidator(self) -> None:
        workflow.logger.info(f"Approve Update Received: Validating")
        if self.approved:
            raise ApplicationError(f"Validation Failed: Transfer already approved")
        if self.transferState != "waiting":
            raise ApplicationError(f"Validation Failed: Transfer doesn't require approval")

    @workflow.query(name="transferStatus")
    def queryTransferStatus(self) -> TransferStatus:
        return TransferStatus(self.progress, self.transferState, "", self.depositResponse, self.approvalTime)

    def upsertStep(self, step: str) -> None:
        if self.ADVANCED_VISIBILITY == self.workflow_type:
            workflow.logger.info(f"Advanced visibility... On step: {step}")
            workflow.upsert_search_attributes([self.WORKFLOW_STEP.value_set(step)])

    async def updateProgress(self, progress: int, sleep: int) -> None:
        await self.updateProgressStatus(progress, sleep, "running")

    async def updateProgressStatus(self, progress: int, sleep: int, transferState: str) -> None:
        if sleep > 0:
            await asyncio.sleep(sleep)

        self.transferState = transferState
        self.progress = progress
