use std::time::Duration;
use temporalio_common::protos::temporal::api::common::v1::RetryPolicy;
use temporalio_macros::activities;
use temporalio_sdk::{
    ApplicationFailure,
    activities::{ActivityContext, ActivityError},
};
use tracing::info;
use uuid::Uuid;

use crate::shared::{API_DOWNTIME, ActivityInput, INVALID_ACCOUNT, TransferInput};

pub struct AccountTransferActivities;

#[activities]
impl AccountTransferActivities {
    pub fn get_retry_policy() -> RetryPolicy {
        RetryPolicy {
            initial_interval: Some(Duration::from_secs(1).try_into().unwrap()),
            maximum_interval: Some(Duration::from_secs(30).try_into().unwrap()),
            backoff_coefficient: 2.0,
            ..Default::default()
        }
    }

    #[activity]
    pub async fn generate_idempotency_key(
        _ctx: ActivityContext,
    ) -> Result<String, ActivityError> {
        let uuid = Uuid::new_v4().to_string();
        Ok(uuid)
    }

    #[activity]
    pub async fn validate(
        _ctx: ActivityContext,
        input: TransferInput,
    ) -> Result<String, ActivityError> {
        info!("Validate Activity has started. Input {:?}", input);
        Self::simulate_external_operation_ms(&1000).await;
        Ok("SUCCESS".to_string())
    }

    #[activity]
    pub async fn withdraw(
        ctx: ActivityContext,
        input: ActivityInput,
    ) -> Result<String, ActivityError> {
        info!("Withdraw activity started. Amount {0}", input.amount);
        let attempt = ctx.info().attempt;
        let error =
            Self::simulate_external_operation(1000, &input.workflow_type, &attempt.into()).await;
        info!(
            "Withdraw call complete, type {:?}, error {:?}",
            input.workflow_type, error
        );
        if error? == API_DOWNTIME {
            // A transient error: return a plain (retryable) application failure so the
            // activity's retry policy keeps retrying until the API "recovers". `.into()`
            // wraps it via ApplicationFailure::new (retryable)
            info!("Withdraw API unavailable, attempt {attempt}");
            return Err(anyhow::anyhow!("Withdraw activity failed, API unavailable").into());
        }
        Ok("SUCCESS".to_string())
    }

    #[activity]
    pub async fn deposit(
        ctx: ActivityContext,
        input: ActivityInput,
    ) -> Result<String, ActivityError> {
        info!("Deposit activity started. amount {:?}", input.amount);
        let attempt = ctx.info().attempt;
        // simulate external API call1
        let activity_result =
            Self::simulate_external_operation(1000, &input.workflow_type, &attempt.into()).await;
        info!(
            "Deposit activity complete. type {:?} error {:?}",
            input.workflow_type, activity_result
        );
        if activity_result? == INVALID_ACCOUNT {
            info!("Deposit failed due to account not existing.");
            return Err(ActivityError::application(
                ApplicationFailure::non_retryable(anyhow::anyhow!(
                    "Deposit activity failed, account is invalid"
                )),
            ));
        }
        Ok("example-transfer-id".to_string())
    }

    #[activity]
    pub async fn send_notification(
        _ctx: ActivityContext,
        input: TransferInput,
    ) -> Result<String, ActivityError> {
        info!("Send notification activity started. input = {:?}", input);

        //simulte external API call
        Self::simulate_external_operation_ms(&1000).await;

        Ok("SUCCESS".to_string())
    }

    #[activity]
    pub async fn undo_withdraw(
        _ctx: ActivityContext,
        _message: String,
    ) -> Result<bool, ActivityError> {
        //simulate external API call
        Self::simulate_external_operation_ms(&1000).await;
        Ok(true)
    }

    async fn simulate_external_operation_ms(ms: &u64) -> () {
        tokio::time::sleep(Duration::from_millis(*ms)).await;
    }

    async fn simulate_external_operation(
        ms: u64,
        workflow_type: &String,
        attempt: &u64,
    ) -> Result<String, ActivityError> {
        Self::simulate_external_operation_ms(&(ms / attempt)).await;
        if *attempt < 5 {
            return Ok(workflow_type.to_string());
        }
        Ok("NoError".to_string())
    }
}
