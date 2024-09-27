from dataclasses import dataclass

"""
export enum ExecutionScenarioObj {
    HAPPY_PATH = "HAPPY_PATH",
    HUMAN_IN_LOOP = "HUMAN_IN_LOOP",
    API_DOWNTIME = "API_DOWNTIME",
    BUG_IN_WORKFLOW = "BUG_IN_WORKFLOW",
    INVALID_ACCOUNT = "INVALID_ACCOUNT"
}

export interface WorkflowParameterObj {
    amountCents: number;
    scenario: ExecutionScenarioObj;
    initialSleepTime: number;
}

export interface ResultObj {
    depositResponse: DepositResponse;
}

export interface StateObj {
    progressPercentage: number;
    transferState: string;
    workflowStatus?: string;
}

export type DepositResponse = {
    chargeId: string;
}

export interface ScheduleParameterObj {
    interval: number;
    count: number;
    amountCents: number;
    scenario: ExecutionScenarioObj;
}

export interface WorkflowStatus {
    workflowId: string | null | undefined;
    workflowStatus: any;
    url?: string;
}
"""


@dataclass
class TransferInput:
    amount: int
    # scenario: str
    # initialSleepTime: int
    fromAccount: str
    toAccount: str


@dataclass
class TransferStatus:
    progressPercentage: int
    transferStatus: str
    workflowStatus: str
    chargeResult: str
    approvalTime: int
