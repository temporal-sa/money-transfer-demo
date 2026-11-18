import { ApplicationFailure, Context, log, sleep } from '@temporalio/activity';
import type { ActivityInput, DepositResponse, TransferInput } from '../types';

export const API_DOWNTIME = 'AccountTransferWorkflowAPIDowntime';
export const INVALID_ACCOUNT = 'AccountTransferWorkflowInvalidAccount';
export const NO_ERROR = 'NoError';
export const SUCCESS = 'SUCCESS';

async function simulateExternalOperationAsync(ms: number): Promise<string> {
  await sleep(ms);
  return SUCCESS;
}

async function simulateExternalOperationAsyncComplex(ms: number, type: string, attempt: number): Promise<string> {
  await simulateExternalOperationAsync(ms / attempt);
  return attempt < 5 ? type : NO_ERROR
}

export async function validateAsync(input: TransferInput): Promise<string> {
  log.info(`Validate activity started, input = ${input}`);

  await simulateExternalOperationAsync(1000);

  return SUCCESS;
}

export async function withdrawAsync(input: ActivityInput): Promise<string> {
  log.info(`Withdraw activity started, amount = ${input.amount}`);

  const context = Context.current();
  const { attempt } = context.info;

  // Simulate External API Call
  const error = await simulateExternalOperationAsyncComplex(1000, input.type, attempt);
  log.info(`Withdraw call complete, type = ${input.type}, error = ${error}`);
  
  if(error == API_DOWNTIME) {
    log.error(`Withdraw API unavailable, attempt = ${attempt}`);

    throw ApplicationFailure.create({
      message: 'Withdraw activity failed, API unavailable',
    });
  }

  return SUCCESS;
}

export async function depositAsync(input: ActivityInput): Promise<DepositResponse> {
  log.info(`Deposit activity started, amount = ${input.amount}`);

  const context = Context.current();
  const { attempt } = context.info;

  const error = await simulateExternalOperationAsyncComplex(1000, input.type, attempt);
  log.info(`Deposit call complete, type = ${input.type}, error = ${error}`);

  if(error == INVALID_ACCOUNT) {
    throw ApplicationFailure.create({
      nonRetryable: true,
      message: 'Deposit activity failed, account is invalid',
    });
  }
  return {chargeId: 'example-transfer-id'};
}

export async function sendNotificationAsync(input: TransferInput): Promise<string> {
  log.info(`Send notification activity started, input = ${input}`);

  await simulateExternalOperationAsync(1000);

  return SUCCESS;
}

export async function undoWithdrawAsync(amount: number): Promise<boolean> {
  log.info(`Undo withdraw activity started, amount = ${amount}`);

  await simulateExternalOperationAsync(1000);

  return true;
}
