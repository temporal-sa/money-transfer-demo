import { MockActivityEnvironment } from '@temporalio/testing';
import { describe, it } from 'mocha';
import * as activities from '../src/activities/index';
import type { ActivityInput, TransferInput } from '../src/types';
import assert from 'assert';

const transferInput:TransferInput = {
  amount: 100,
  fromAccount: 'account1',
  toAccount: 'account2'
}

const activityInput: ActivityInput = {
  idempotencyKey: 'key123',
  amount: 100,
  type: 'AccountTransferWorkflow'
}

describe('validateAsync activity', async () => {
  it('successfully Validate Transfer Input', async () => {
    const env = new MockActivityEnvironment();
    const result = await env.run(activities.validateAsync, transferInput);
    assert.equal(result, activities.SUCCESS);
  });
});

describe('withdrawAsync activity', async () => {
  it('successfully withdraws funds', async () => {
    const env = new MockActivityEnvironment();
    const result = await env.run(activities.withdrawAsync, activityInput);
    assert.equal(result, activities.SUCCESS);
  });
});

describe('depositAsync activity', async () => {
  it('successfully deposits funds', async () => {
    const env = new MockActivityEnvironment();
    const result = await env.run(activities.depositAsync, activityInput);
    assert.deepEqual(result, { chargeId: 'example-transfer-id' });
  });
});

describe('sendNotificationAsync activity', async () => {
  it('successfully Send Notification', async () => {
    const env = new MockActivityEnvironment();
    const result = await env.run(activities.sendNotificationAsync, transferInput);
    assert.equal(result, activities.SUCCESS);
  });
});

describe('undoWithdrawAsync activity', async () => {
  it('successfully Undo Withdraw', async () => {
    const env = new MockActivityEnvironment();
    const amount = 100;
    const result = await env.run(activities.undoWithdrawAsync, amount);
    assert.equal(result, true);
  });
});