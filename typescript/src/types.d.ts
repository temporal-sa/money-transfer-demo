export interface DepositResponse {
  chargeId: string;
}

export interface TransferInput {
  amount: number;
  fromAccount: string;
  toAccount: string;
}

export interface ActivityInput {
  idempotencyKey: string;
  amount: number;
  type: string;
}

export interface TransferOutput {
  depositResponse: DepositResponse;
}

export interface TransferStatus {
  progressPercentage: number;
  transferState: string;
  workflowStatus: string;
  chargeResult: DepositResponse;
  approvalTime: number;
}