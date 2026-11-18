import { TestWorkflowEnvironment } from '@temporalio/testing';
import { after, before, it } from 'mocha';
import { Worker } from '@temporalio/worker';
import { AccountTransferWorkflow } from '../src/workflows/AccountTransferWorkflow/index';
import * as activities from '../src/activities/index';
import assert from 'assert';
import { TransferInput, TransferOutput, DepositResponse } from '../src/types';

const taskQueue = 'MoneyTransfer';

const transferInput:TransferInput = {
  amount: 100,
  fromAccount: 'account1',
  toAccount: 'account2'
}

const depositResponse: DepositResponse = {
  chargeId: 'example-transfer-id'
}

const transferOutput:TransferOutput = {
  depositResponse
}

describe('Testing Happy Path', function () {
  let testEnv: TestWorkflowEnvironment;
   this.timeout(60000);

  before(async () => {
    testEnv = await TestWorkflowEnvironment.createTimeSkipping();
    
  });

  after(async () => {
    await testEnv?.teardown();
  });

  it('successfully completes the Workflow with a mocked Activity', async () => {
    const { client, nativeConnection } = testEnv;

    const worker = await Worker.create({
      connection: nativeConnection,
      taskQueue,
      workflowsPath: require.resolve('../src/workflows/index'),
      activities
    });

    const result = await worker.runUntil(
      client.workflow.execute(AccountTransferWorkflow, {
        args: [transferInput],
        workflowId: 'test',
        taskQueue,
      })
    );
    assert.deepStrictEqual(result, transferOutput);
  });
});