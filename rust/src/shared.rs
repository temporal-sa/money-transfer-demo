use std::fmt;

pub const TASK_QUEUE: &str = "MoneyTransfer";
pub const API_DOWNTIME: &str = "AccountTransferWorkflowAPIDowntime";
pub const INVALID_ACCOUNT: &str = "AccountTransferWorkflowInvalidAccount";

#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TransferInput {
    pub amount: u32,
    pub from_account: String,
    pub to_account: String,
}

#[derive(Debug, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TransferOutput {
    pub deposit_response: String,
}

#[derive(Clone, Default, Debug, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DepositResponse {
    pub charge_id: String,
}

#[derive(Clone, Default, Debug, serde::Serialize, serde::Deserialize)]
pub struct ActivityInput {
    pub idempotency_key: String,
    pub amount: u64,
    pub workflow_type: String,
}

#[derive(Clone, Default, Debug, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TransferStatus {
    pub progress_percentage: u64,
    pub transfer_state: String,
    pub workflow_status: String,
    pub charge_result: DepositResponse,
    pub approval_time: u64,
}

#[derive(Clone, Default, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum TransferState {
    #[default]
    NoneType,
    Waiting,
    Running,
    Finished,
}

// Implement the Display trait
impl fmt::Display for TransferState {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let text = match self {
            TransferState::NoneType => "",
            TransferState::Waiting => "waiting",
            TransferState::Running => "running",
            TransferState::Finished => "finished",
        };
        write!(f, "{}", text)
    }
}