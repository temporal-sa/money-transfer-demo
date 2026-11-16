from dataclasses import dataclass

@dataclass
class DepositResponse:
    def __init__(self, chargeId: str) -> None:
        self.chargeId = chargeId

    chargeId: str           # TODO: Refactor to allow different name for JSON vs variable

    def get_chargeId(self):
        return self.chargeId

@dataclass
class TransferInput:
    amount: int
    fromAccount: str
    toAccount: str

@dataclass
class ActivityInput:
    idempotencyKey: str
    amount: float
    workflowType: str

@dataclass
class TransferOutput:
    def __init__(self, depositResponse: str) -> None:
        self.depositResponse = depositResponse

    depositResponse: str

@dataclass
class TransferStatus:
    def __init__(self, progress: int, transferState: str, workflowStatus: str, depositResponse: DepositResponse, approvalTime: int) -> None:
        self.progressPercentage = progress
        self.transferState = transferState
        self.workflowStatus = workflowStatus
        self.chargeResult = depositResponse
        self.approvalTime = approvalTime

    progressPercentage: int
    transferState: str
    workflowStatus: str
    chargeResult: DepositResponse   # TODO: Refactor to allow different name for JSON vs variable
    approvalTime: int
