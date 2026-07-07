#![allow(unreachable_pub)]
use std::time::Duration;
use temporalio_common::protos::temporal::api::common::v1::RetryPolicy;
use temporalio_macros::{workflow, workflow_methods};
use temporalio_sdk::{
    ActivityOptions, LocalActivityOptions, TimerOptions, WorkflowContext, WorkflowContextView,
    WorkflowResult,
};
use tracing::info;

use crate::activities::AccountTransferActivities;
use crate::shared::{
    ActivityInput, DepositResponse, TransferInput, TransferOutput, TransferStatus,
};

#[derive(Default, Debug, serde::Serialize, serde::Deserialize)]
#[workflow]
pub struct AccountTransferWorkflow {
    progress: u64,
    transfer_state: String,
    deposit_response: DepositResponse,
    sched_to_close_timeout: u64,
    idempotency_key: String,
    workflow_type: String,
    retry_policy: RetryPolicy,
}

#[workflow_methods]
impl AccountTransferWorkflow {
    #[init]
    pub fn new(ctx: &WorkflowContextView) -> Self {
        Self {
            workflow_type: ctx.workflow_type.clone(),
            progress: 0u64,
            deposit_response: DepositResponse {
                charge_id: "".to_string(),
            },
            idempotency_key: "".to_string(),
            sched_to_close_timeout: 0u64,
            transfer_state: "".to_string(),
            retry_policy: AccountTransferActivities::get_retry_policy(),
        }
    }

    #[run]
    pub async fn run(
        ctx: &mut WorkflowContext<Self>,
        input: TransferInput,
    ) -> WorkflowResult<TransferOutput> {
        let workflow_type = ctx.state(|s| s.workflow_type.clone());
        info!(
            "Simple Workflow started {} with input: {:?}",
            workflow_type, input
        );
        let info = ctx.workflow_initial_info();
        info!("Workflow info: {:?}", info);

        //generate the idempotency key with a local activity. UUID generation not supported yet
        //in the Rust SDK.
        let handle = ctx
            .start_local_activity(
                AccountTransferActivities::generate_idempotency_key,
                (),
                LocalActivityOptions {
                    start_to_close_timeout: Some(Duration::from_secs(30)),
                    ..Default::default()
                },
            )
            .await?;

        //save the idempotency key and then hydrate a new variable for use by later activities
        ctx.state_mut(|s| {
            s.idempotency_key = handle;
            info!("Idempotency key set to {}", s.idempotency_key)
        });
        let idempotency_key = ctx.state(|s| s.idempotency_key.clone());

        let amount = input.amount.into();

        let activity_input = ActivityInput {
            idempotency_key,
            amount,
            workflow_type,
        };

        //validate
        let _handle = ctx
            .start_activity(
                AccountTransferActivities::validate,
                input.clone(),
                ActivityOptions::start_to_close_timeout(Duration::from_secs(30)),
            )
            .await?;
        Self::update_progress(ctx, 25u64, 1u64, None).await;

        //withdraw
        let _handle = ctx
            .start_activity(
                AccountTransferActivities::withdraw,
                activity_input.clone(),
                ActivityOptions::start_to_close_timeout(Duration::from_secs(30)),
            )
            .await?;
        Self::update_progress(ctx, 50u64, 3u64, None).await;

        //deposit
        let handle = ctx
            .start_activity(
                AccountTransferActivities::deposit,
                activity_input.clone(),
                ActivityOptions::start_to_close_timeout(Duration::from_secs(30)),
            )
            .await?;
        info!("after deposit {:?}", handle);
        ctx.state_mut(|s| {
            s.deposit_response = DepositResponse { charge_id: handle };
        });
        Self::update_progress(ctx, 75u64, 1u64, None).await;

        //notification
        let handle = ctx
            .start_activity(
                AccountTransferActivities::send_notification,
                input,
                ActivityOptions::start_to_close_timeout(Duration::from_secs(30)),
            )
            .await?;
        info!("notification response {:?}", handle);
        Self::update_progress(ctx, 100u64, 1u64, Some("finished".to_string())).await;
        let results: TransferOutput = TransferOutput {
            deposit_response: ctx.state(|s| s.deposit_response.charge_id.clone()),
        };
        info!("Returning {:?}", results);
        Ok(results)
    }

    async fn update_progress(
        ctx: &mut WorkflowContext<Self>,
        progress: u64,
        sleep: u64,
        transfer_state: Option<String>,
    ) -> () {
        ctx.state_mut(|s| {
            s.progress = progress;
            if let Some(ts) = transfer_state {
                s.transfer_state = ts;
            }
        });

        if sleep > 0 {
            ctx.timer(TimerOptions {
                duration: Duration::from_secs(sleep),
                summary: Some("update progress timer".into()),
            })
            .await;
        };
    }

    #[query(name = "transferStatus")]
    pub fn query_transfer_status(&self, _ctx: &WorkflowContextView) -> TransferStatus {
        TransferStatus {
            progress_percentage: self.progress,
            transfer_state: self.transfer_state.clone(),
            workflow_status: "".to_string(),
            charge_result: self.deposit_response.clone(),
            approval_time: 0,
        }
    }
}
