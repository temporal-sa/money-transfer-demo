import {
  proxyActivities,
  proxyLocalActivities,
  sleep,
  workflowInfo,
  defineQuery,
  defineSignal,
  defineUpdate,
  upsertSearchAttributes,
  ActivityFailure,
  setHandler,
  log,
  uuid4,
  condition,
  ApplicationFailure,
} from '@temporalio/workflow';
import type * as activities from '../../activities/index';
import type { RetryPolicy } from '@temporalio/client';
import type { DepositResponse, TransferInput, TransferOutput, TransferStatus } from "../../types";

const DEFAULT_RETRY_POLICY: RetryPolicy = {
  initialInterval: '1s',
  maximumInterval: '30s',
  backoffCoefficient: 2,
};

const { validateAsync, withdrawAsync, depositAsync, sendNotificationAsync, undoWithdrawAsync } = proxyActivities<typeof activities>({
  startToCloseTimeout: '5s',
  retry: DEFAULT_RETRY_POLICY,
});

const transferStatusQuery = defineQuery<TransferStatus>('transferStatus');
const approveTransferSignal = defineSignal<[null]>('approveTransfer');
const approveTransferUpdate = defineUpdate<string, []>('approveTransferUpdate');

export async function AccountTransferWorkflowScenarios(input: TransferInput): Promise<TransferOutput> {
  const { workflowType } = workflowInfo();

  let progress:number, transferState:string;
  let approvalTime = 30;
  let approved = false;
  let depositResponse:DepositResponse = {
    chargeId: ''
  }

  // Set Query
  setHandler(transferStatusQuery, () => {
    return {
      transferState,
      approvalTime,
      progressPercentage: progress,
      workflowStatus: '',
      chargeResult: depositResponse,
     }
  });

  // Set Signal 
  setHandler(approveTransferSignal, () => {
    log.info(`Approve Signal Received`);

    if(transferState === TRANSFER_STATE.WAITING) {
      approved = true;
    } else {
      log.info(`ignal not applied: Transfer is not waiting for approval`);
    }
  });

  // Set Update
  setHandler(
    approveTransferUpdate,
    () => {
      log.info('Approve Update Validated: Approving Transfer');

      approved = true;
      return 'successfully approved transfer';
    },
    {
      validator: (): void => {
        log.info(`Approve Update Received: Validating`);
        
        if(approved) {
          throw new Error(`Validation Failed: Transfer already approved`);
        } else if(transferState != TRANSFER_STATE.WAITING) {
          throw new Error(`Validation Failed: Transfer doesn't require approval`);
        }
      },
    },
  );

  log.info(`Dynamic Account Transfer workflow started, type = ${workflowType}`);
  const idempotencyKey = uuid4();

  // Validate
  await upsertStep('Validate');
  await validateAsync(input);
  ({progress, transferState } = await updateProgressAsync(25, 1));

  if(WF_TYPES.NEEDS_APPROVAL == workflowType) {
    log.info(`Waiting on 'approveTransfer' Signal or Update for workflow ID: ${workflowInfo().workflowId}`);
    ({progress, transferState } = await updateProgressAsyncComplex(30, 0, TRANSFER_STATE.WAITING));

    if(await condition(() => approved, `${approvalTime}s`)) {
      // Approval has came in time!
    } else {
      // Approval didn't came in time :(
      log.info(`Approval not received within the ${approvalTime}-second time window: Failing the workflow.`);
      throw ApplicationFailure.create({message : `Approval not received within ${approvalTime} seconds`, type: 'timeout'});
    }
  }

  // Withdraw
  await upsertStep('Withdraw');
  await withdrawAsync(idempotencyKey, input.amount, workflowType);
  ({progress, transferState } = await updateProgressAsync(50, 3));

  if(WF_TYPES.BUG == workflowType) {
    // Simulate bug
    throw new Error("Simulate bug - fix me!");
  }

  // Deposit
  await upsertStep('Deposit');

  try {
    depositResponse = await depositAsync(idempotencyKey, input.amount, workflowType);
    ({progress, transferState } = await updateProgressAsync(75, 1));
  } catch(err) {
    // if deposit fails in an unrecoverable way, rollback the withdrawal and fail the workflow
    log.error('Deposit failed unrecoverable error, reverting withdraw');

    // Undo Withdraw (rollback)
    await undoWithdrawAsync(input.amount);
    
    // return failure message
    throw err;
  }

  // Send Notification
  await upsertStep('Send Notification');
  await sendNotificationAsync(input);
  ({progress, transferState } = await updateProgressAsyncComplex(100, 0, TRANSFER_STATE.FINISHED));

  return {depositResponse};
}

async function upsertStep(step: string) {
  if (WF_TYPES.VISIBILITY == workflowInfo().workflowType) {
    upsertSearchAttributes({
      Step: [step],
    });
  }
}

async function updateProgressAsync(progress: number, sleepDuration: number) {
  return updateProgressAsyncComplex(progress, sleepDuration, TRANSFER_STATE.RUNNING);
}

async function updateProgressAsyncComplex(progress: number, sleepDuration: number, transferState: string) {
  if(sleepDuration > 0) {
    await sleep(sleepDuration);
  }

  return {transferState, progress};
}

// Exported Workflow Scenarios
export const AccountTransferWorkflowRecoverableFailure = AccountTransferWorkflowScenarios;
export const AccountTransferWorkflowHumanInLoop = AccountTransferWorkflowScenarios;
export const AccountTransferWorkflowAdvancedVisibility = AccountTransferWorkflowScenarios;
export const AccountTransferWorkflowAPIDowntime = AccountTransferWorkflowScenarios;
export const AccountTransferWorkflowInvalidAccount = AccountTransferWorkflowScenarios;

const WF_TYPES = {
  BUG: 'AccountTransferWorkflowRecoverableFailure',
  NEEDS_APPROVAL: 'AccountTransferWorkflowHumanInLoop',
  VISIBILITY: 'AccountTransferWorkflowAdvancedVisibility',
} as const;

const TRANSFER_STATE = {
  RUNNING: 'running',
  WAITING : 'waiting',
  FINISHED : 'finished'
} as const;