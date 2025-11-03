import asyncio
import os
from temporalio.client import Client
from temporalio.common import WorkerDeploymentVersion, VersioningBehavior
from temporalio.worker import Worker, WorkerDeploymentConfig
from temporalio import workflow, activity


@workflow.defn
class AccountTransferWorkflow:
    @workflow.run
    async def run(self, transfer_request: dict) -> str:
        for i in range(100):
            await workflow.sleep(2)
            workflow.logger.info(f"Processing transfer step {i}")
        return f"Transfer of {transfer_request['amount']} from {transfer_request['fromAccount']} to {transfer_request['toAccount']} completed"


async def main():
    temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    temporal_namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
    task_queue = os.getenv("TEMPORAL_TASK_QUEUE", "MoneyTransfer")
    build_id = os.getenv("TEMPORAL_WORKER_BUILD_ID", "1.0.0")
    deployment_name = os.getenv("TEMPORAL_DEPLOYMENT_NAME", "money-transfer-worker-deployment")
    
    client = await Client.connect(temporal_address, namespace=temporal_namespace)
    
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[AccountTransferWorkflow],
        deployment_config=WorkerDeploymentConfig(
            version=WorkerDeploymentVersion(
                deployment_name=deployment_name,
                build_id=build_id
            ),
            use_worker_versioning=True,
            default_versioning_behavior=VersioningBehavior.AUTO_UPGRADE
        ),
    )
    
    print(f"Starting worker with build_id: {build_id}, deployment: {deployment_name}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
