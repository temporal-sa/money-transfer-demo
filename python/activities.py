import asyncio
import logging
from datetime import timedelta
from temporalio import activity
from temporalio.common import RetryPolicy
from shared_objects import TransferInput, DepositResponse
from temporalio.exceptions import ApplicationError

logging.basicConfig(level=logging.INFO)

class AccountTransferActivities:

    API_DOWNTIME = "AccountTransferWorkflowAPIDowntime"
    INVALID_ACCOUNT = "AccountTransferWorkflowInvalidAccount"
    DEPOSIT_BATCHES = 6

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
    async def withdraw(self, idempotencyKey: str, amount: float, workflow_type: str) -> str:
        activity.logger.info(f"Withdraw activity started. amount {amount}")
        attempt = activity.info().attempt

        # simulate external API call
        error = await self.simulate_external_operation(1000, workflow_type, attempt)
        activity.logger.info(f"Withdraw call complete, type {workflow_type}, error {error}")

        if self.API_DOWNTIME == error:
            # transient error, which can be retried
            activity.logger.info(f"Withdraw API unavaiable, attempt {attempt}")
            raise ApplicationError(f"Withdraw activity failed, API unavailable")

        return "SUCCESS"

    @activity.defn
    async def deposit(self, idempotencyKey: str, amount: float, workflow_type: str) -> DepositResponse:
        activity.logger.info(f"Deposit activity started. amount {amount}")
        attempt = activity.info().attempt

        # simulate external API call
        error = await self.simulate_external_operation(1000, workflow_type, attempt)
        activity.logger.info(f"Deposit activity complete. type {workflow_type} error {error}")

        if self.INVALID_ACCOUNT == error:
            # business error, which cannot be retried
            raise ApplicationError(f"Deposit activity failed, account is invalid", type="InvalidAccount", non_retryable=True)

        # Post the deposit in batches, checking in with Temporal after each one.
        # If the Worker dies, the retry picks up after the last batch it reported, not from the start.
        details = activity.info().heartbeat_details
        done = details[0] if details else 0
        if done:
            activity.logger.info(f"Deposit resuming after batch {done} of {self.DEPOSIT_BATCHES}")
        for batch in range(done + 1, self.DEPOSIT_BATCHES + 1):
            await self.simulate_external_operation_ms(1500)
            activity.heartbeat(batch, f"Batch {batch} of {self.DEPOSIT_BATCHES} posted")
            activity.logger.info(f"Deposit batch {batch} of {self.DEPOSIT_BATCHES} posted")

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
