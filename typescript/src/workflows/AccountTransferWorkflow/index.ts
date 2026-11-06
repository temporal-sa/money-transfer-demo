import {
  proxyActivities,
  sleep,
  workflowInfo,
  defineQuery,
  setHandler,
  log,
  uuid4,
  RetryPolicy,
} from '@temporalio/workflow';
import type * as activities from '../../activities/index';
import type { DepositResponse, TransferInput, TransferOutput, TransferStatus } from "../../types";

const DEFAULT_RETRY_POLICY: RetryPolicy = {
  initialInterval: '1s',
  maximumInterval: '30s',
  backoffCoefficient: 2,
};

const { validateAsync, withdrawAsync, depositAsync, sendNotificationAsync } =
proxyActivities<typeof activities>({
  startToCloseTimeout: '5s',
  retry: DEFAULT_RETRY_POLICY,
});

const transferStatusQuery = defineQuery<TransferStatus>('transferStatus');

export async function AccountTransferWorkflow(input: TransferInput): Promise<TransferOutput> {
  const { workflowType } = workflowInfo();

  let progress:number, transferState:string;
  let depositResponse:DepositResponse = {
    chargeId: ''
  }

  setHandler(transferStatusQuery, () => {
    return {
      transferState,
      progressPercentage: progress,
      workflowStatus: '',
      chargeResult: depositResponse,
      approvalTime: 0
     }
  });

  log.info(`Account Transfer workflow started, type = ${workflowType}`);
  const idempotencyKey = uuid4();

  // Validate
  await validateAsync(input);
  ({progress, transferState } = await updateProgressAsync(25, 1));

  // Withdraw
  await withdrawAsync(idempotencyKey, input.amount, workflowType);
  ({progress, transferState } = await updateProgressAsync(50, 3));

  // Deposit
  depositResponse = await depositAsync(idempotencyKey, input.amount, workflowType);
  ({progress, transferState } = await updateProgressAsync(75, 1));

  // Send Notification
  await sendNotificationAsync(input);
  ({progress, transferState } = await updateProgressAsyncComplex(100, 0, 'finished'));

  return {depositResponse};
}

async function updateProgressAsync(progress: number, sleepDuration: number) {
  return updateProgressAsyncComplex(progress, sleepDuration, 'running');
}

async function updateProgressAsyncComplex(progress: number, sleepDuration: number, transferState: string) {
  if(sleepDuration > 0) {
    await sleep(sleepDuration);
  }

  return {transferState, progress};
}