import asyncio
from datetime import timedelta
import dataclasses
import logging
import os

import temporalio.converter
from temporalio.client import (
    Client,
    ClientConfig,
    TLSConfig,
)
from temporalio.worker import Worker

from account_transfer_workflow import AccountTransferWorkflow
from account_transfer_workflow_scenarios import AccountTransferWorkflowScenarios
from activities import AccountTransferActivities
from codec import EncryptionCodec
from narrative import NarrativeInterceptor

async def build_client():
    address = os.getenv("TEMPORAL_ADDRESS", "127.0.0.1:7233")
    namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
    tlsCertPath = os.getenv("TEMPORAL_CERT_PATH", "")
    tlsKeyPath = os.getenv("TEMPORAL_KEY_PATH", "")
    apiKey = os.getenv("TEMPORAL_API_KEY", "")
    encryptPayloads = True if os.getenv("ENCRYPT_PAYLOADS", "").lower() == "true" else False

    config = ClientConfig(
        target_host=address,
        namespace=namespace,
    )

    if encryptPayloads:
        print("Encrypting payloads")
        config["data_converter"] = dataclasses.replace(temporalio.converter.default(), payload_codec=EncryptionCodec())

    # Prefer API Key auth
    if apiKey != "":
        print("Using Cloud API key auth")
        print(f"API Key: {apiKey[:4]}...{apiKey[-4:]}")
        print(f"Address: {address}")
        print(f"Namespace: {namespace}")
        config["api_key"] = apiKey
        config["tls"] = True
    # Fallback to mTLS auth
    elif tlsCertPath and tlsKeyPath:
        print("Using mTLS auth")
        with open(tlsCertPath, "rb") as f:
            cert = f.read()
        with open(tlsKeyPath, "rb") as f:
            key = f.read()
        config["tls"] = TLSConfig(client_cert=cert, client_private_key=key)

    return await Client.connect(**config)

async def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)s | %(filename)s:%(lineno)s | %(message)s")

    taskQueue = os.getenv("TEMPORAL_TASK_QUEUE", "MoneyTransfer")
    address = os.getenv("TEMPORAL_ADDRESS", "127.0.0.1:7233")

    client = await build_client()

    activities = AccountTransferActivities()

    # Writes the transfer's story into the Temporal UI; see narrative.py

    worker = Worker(
        client,
        task_queue=taskQueue,
        workflows=[AccountTransferWorkflow, AccountTransferWorkflowScenarios],
        activities=[activities.validate,
                    activities.withdraw,
                    activities.deposit,
                    activities.sendNotification,
                    activities.undoWithdraw],
        interceptors=[NarrativeInterceptor()],
        # Send each Deposit batch's heartbeat within a second, so the UI shows the latest batch (the SDK's default batches them up)
        max_heartbeat_throttle_interval=timedelta(seconds=1),
    )
    print(f"Connecting to Temporal on {address}")
    print("Python money transfer worker starting...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
