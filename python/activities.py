import asyncio
import logging
from datetime import timedelta
from temporalio import activity
from temporalio.common import RetryPolicy
from shared_objects import ActivityInput, TransferInput, DepositResponse
from temporalio.exceptions import ApplicationError

logging.basicConfig(level=logging.INFO)

class AccountTransferActivities:

    API_DOWNTIME = "AccountTransferWorkflowAPIDowntime"
    INVALID_ACCOUNT = "AccountTransferWorkflowInvalidAccount"

    retry_policy = RetryPolicy(initial_interval=timedelta(seconds=1), backoff_coefficient=2, maximum_interval=timedelta(seconds=30))

    async def simulate_external_operation_ms(self, ms: int):
        try:
            await asyncio.sleep(ms / 1000)
            # await time.sleep(ms / 1000)
        except InterruptedError as e:
            print(e.__traceback__)

    async def simulate_external_operation(self, ms: int, workflow_type: str, attempt: int):
        await self.simulate_external_operation_ms(ms / attempt)
        return workflow_type if attempt < 5 else "NoError"

    @activity.defn
    async def validate(self, input: TransferInput) -> str:
        activity.logger.info(f"Validate activity started. Input {input}")

        # simulate external API call
        await self.simulate_external_operation_ms(1000)

        return "SUCCESS"

    @activity.defn
    async def withdraw(self, input: ActivityInput) -> str:
        activity.logger.info(f"Withdraw activity started. amount {input.amount}")
        attempt = activity.info().attempt

        # simulate external API call
        error = await self.simulate_external_operation(1000, input.workflowType, attempt)
        activity.logger.info(f"Withdraw call complete, type {input.workflowType}, error {error}")

        if self.API_DOWNTIME == error:
            # transient error, which can be retried
            activity.logger.info(f"Withdraw API unavaiable, attempt {attempt}")
            raise ApplicationError(f"Withdraw activity failed, API unavailable")

        return "SUCCESS"

    @activity.defn
    async def deposit(self, input: ActivityInput) -> DepositResponse:
        activity.logger.info(f"Deposit activity started. amount {input.amount}")
        attempt = activity.info().attempt

        # simulate external API call
        error = await self.simulate_external_operation(1000, input.workflowType, attempt)
        activity.logger.info(f"Deposit activity complete. type {input.workflowType} error {error}")

        if self.INVALID_ACCOUNT == error:
            # business error, which cannot be retried
            raise ApplicationError(f"Deposit activity failed, account is invalid", type="InvalidAccount", non_retryable=True)

        return DepositResponse("example-transfer-id")

    @activity.defn
    async def sendNotification(self, input: TransferInput) -> str:
        activity.logger.info(f"Send notification activity started. input = {input}")

        # simulte external API call
        await self.simulate_external_operation_ms(1000)

        return "SUCCESS"

    @activity.defn
    async def undoWithdraw(self, amount: float) -> bool:

        # simulate external API call
        await self.simulate_external_operation_ms(1000)

        return True
