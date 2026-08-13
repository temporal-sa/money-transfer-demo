#![allow(unreachable_pub)]
use std::time::Duration;
use temporalio_common::protos::temporal::api::common::v1::RetryPolicy;
use temporalio_common::search_attributes::SearchAttributeKey;
use temporalio_macros::{workflow, workflow_methods};
use temporalio_sdk::{
    ActivityOptions, ApplicationFailure, TimerOptions, WorkflowContext,
    WorkflowContextView, WorkflowResult, WorkflowTermination, SyncWorkflowContext
};
use tracing::{error, info, warn};

use crate::activities::AccountTransferActivities;
use crate::shared::{
    ActivityInput, DepositResponse, TransferInput, TransferOutput, TransferStatus, TransferState
};

// The Rust SDK registers one workflow type name per struct and has no dynamic-workflow
// To serve every scenario the UI can start, we stamp out one workflow struct per scenario
// type name from a single shared body. The body branches on `ctx.workflow_type`
// (which equals each struct's registered `#[run(name = ...)]`), so the same code drives every scenario.
macro_rules! account_transfer_scenario {
    ($struct:ident, $wf_type:literal) => {
        #[derive(Default, Debug, serde::Serialize, serde::Deserialize)]
        #[workflow]
        pub struct $struct {
            workflow_type: String,
            progress: u64,
            deposit_response: DepositResponse,
            idempotency_key: String,
            sched_to_close_timeout: u64,
            transfer_state: TransferState,
            retry_policy: RetryPolicy,
            approval_time: u64,
            approved: bool,
        }

        #[workflow_methods]
        impl $struct {
            const BUG: &str = "AccountTransferWorkflowRecoverableFailure";
            const NEEDS_APPROVAL: &str = "AccountTransferWorkflowHumanInLoop";
            const ADVANCED_VISIBILITY: &str = "AccountTransferWorkflowAdvancedVisibility";
            const SEARCH_ATTRIBUTE: SearchAttributeKey<String> =
                SearchAttributeKey::keyword("Step");

            #[init]
            fn new(ctx: &WorkflowContextView) -> Self {
                Self {
                    workflow_type: ctx.workflow_type().to_string(),
                    progress: 0u64,
                    deposit_response: DepositResponse {
                        charge_id: "".to_string(),
                    },
                    idempotency_key: "".to_string(),
                    sched_to_close_timeout: 5u64,
                    transfer_state: TransferState::NoneType,
                    retry_policy: AccountTransferActivities::get_retry_policy(),
                    approval_time: 30u64,
                    approved: false,
                }
            }

            #[run(name = $wf_type)]
            pub async fn run(
                ctx: &mut WorkflowContext<Self>,
                input: TransferInput,
            ) -> WorkflowResult<TransferOutput> {
                ctx.state(|s| {
                    info!(
                        "Dynamic Account Transfer Workflow started {:?}, input = {:?}",
                        s.workflow_type, input
                    );
                });

                //generate the idempotency key within workflow context
                let idempotency_key = ctx.uuid4();
                ctx.state_mut(|s| {
                    s.idempotency_key = idempotency_key.clone();
                    info!("Idempotency key set to {}", s.idempotency_key)
                });
                let amount = input.amount.into();

                let activity_input = ActivityInput {
                    idempotency_key,
                    amount,
                    workflow_type: ctx.state(|s| s.workflow_type.clone()),
                };

                //validate
                Self::upsert_step(ctx, "Validate".to_string()).await;
                let _handle = ctx
                    .execute_activity(
                        AccountTransferActivities::validate,
                        input.clone(),
                        ActivityOptions::start_to_close_timeout(Duration::from_secs(30)),
                    )
                    .await?;
                Self::update_progress(ctx, 25u64, 1u64).await;

                if Self::NEEDS_APPROVAL == activity_input.workflow_type {
                    let info = ctx.info();
                    info!(
                        "Waiting on 'approveTransfer' Signal or Update for workflow ID: {:?}",
                        info.workflow_id()
                    );
                    Self::update_progress_status(ctx, 30, 0, TransferState::Waiting).await;

                    // Wait for approval for up to approval_time seconds.
                    let approval_time = ctx.state(|s| s.approval_time);
                    let approved = temporalio_sdk::workflows::select! {
                        _ = ctx.timer(Duration::from_secs(approval_time)) => false,
                        _ = ctx.wait_condition(|s: &Self| s.approved) => true,
                    };
                    if !approved {
                        error!("Approval not received within {approval_time} seconds");
                        return Err(WorkflowTermination::failed_application(
                            ApplicationFailure::builder(anyhow::anyhow!(
                                "Approval not received within {approval_time} seconds"
                            ))
                            .type_name("ApprovalTimeout".to_string())
                            .non_retryable(true)
                            .build(),
                        ));
                    }
                }

                //withdraw
                Self::upsert_step(ctx, "Withdraw".to_string()).await;
                let _handle = ctx
                    .execute_activity(
                        AccountTransferActivities::withdraw,
                        activity_input.clone(),
                        ActivityOptions::start_to_close_timeout(Duration::from_secs(30)),
                    )
                    .await?;
                Self::update_progress(ctx, 50u64, 3u64).await;

                // Recoverable-failure scenario: a panic fails the workflow *task* (not the
                if Self::BUG == activity_input.workflow_type {
                    //BUG: comment out the next two lines and uncomment the info! statement line
                    error!("There's a bug!");
                    panic!("Simulated bug - fix me!");
                    //info!("Bug is fixed!");
                }

                //deposit
                Self::upsert_step(ctx, "Deposit".to_string()).await;
                let handle = match ctx
                    .execute_activity(
                        AccountTransferActivities::deposit,
                        activity_input.clone(),
                        ActivityOptions::start_to_close_timeout(Duration::from_secs(30)),
                    )
                    .await
                {
                    Ok(h) => h,
                    Err(e) => {
                        // Deposit failed unrecoverably: roll back the withdraw (saga
                        // compensation), then fail the workflow non-retryably.
                        warn!("Deposit failed unrecoverable error, reverting withdraw");
                        ctx.execute_activity(
                            AccountTransferActivities::undo_withdraw,
                            "reverting withdraw".to_string(),
                            ActivityOptions::start_to_close_timeout(Duration::from_secs(30)),
                        )
                        .await?;
                        return Err(WorkflowTermination::failed_application(
                            ApplicationFailure::builder(anyhow::anyhow!("Deposit failed: {e}"))
                                .type_name("DepositFailed".to_string())
                                .non_retryable(true)
                                .build(),
                        ));
                    }
                };
                info!("after deposit {:?}", handle);
                ctx.state_mut(|s| {
                    s.deposit_response = DepositResponse { charge_id: handle };
                });
                Self::update_progress(ctx, 75u64, 1u64).await;

                //notification
                Self::upsert_step(ctx, "Notify".to_string()).await;
                let handle = ctx
                    .execute_activity(
                        AccountTransferActivities::send_notification,
                        input.clone(),
                        ActivityOptions::start_to_close_timeout(Duration::from_secs(30)),
                    )
                    .await?;
                info!("notification response {:?}", handle);
                Self::update_progress_status(ctx, 100u64, 1u64, TransferState::Finished).await;
                let results: TransferOutput = TransferOutput {
                    deposit_response: ctx.state(|s| s.deposit_response.charge_id.clone()),
                };
                info!("Returning {:?}", results);
                Ok(results)
            }

            #[signal(name = "approveTransfer")]
            pub fn approve_transfer_signal(&mut self, _ctx: &mut SyncWorkflowContext<Self>) {
                info!("Approve Signal Received");
                if self.transfer_state == TransferState::Waiting {
                    self.approved = true;
                } else {
                    info!("Approval not applied. Transfer is not waiting for approval");
                }
             }

            #[update(name = "approveTransferUpdate")]
            pub fn approve_transfer_update(&mut self, _ctx: &mut SyncWorkflowContext<Self>) -> String {
                info!("Approve Update Validated: Approving Transfer");
                self.approved = true;
                "successfully approved transfer".to_string()
            }

            #[update_validator(approve_transfer_update)]
            fn approve_transfer_update_validator(
                &self,
                _ctx: &WorkflowContextView,
                _input: &(),
            ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
                info!("Approve Update Received: Validating");
                if self.approved {
                    return Err("Validation Failed: Transfer already approved".into());
                }
                if self.transfer_state != TransferState::Waiting {
                    return Err("Validation Failed: Transfer doesn't require approval".into());
                }
                Ok(())
            }

            async fn upsert_step(ctx: &mut WorkflowContext<Self>, step: String) {
                let advanced = ctx.state(|s| s.workflow_type == Self::ADVANCED_VISIBILITY);
                if advanced {
                    info!("Advanced visibility... On step: {step}");
                    ctx.upsert_search_attributes([Self::SEARCH_ATTRIBUTE.value_set(step)]);
                }
            }

            #[query(name = "transferStatus")]
            pub fn query_transfer_status(&self, _ctx: &WorkflowContextView) -> TransferStatus {
                TransferStatus {
                    progress_percentage: self.progress.clone(),
                    transfer_state: self.transfer_state.to_string(),
                    workflow_status: "".to_string(),
                    charge_result: self.deposit_response.clone(),
                    approval_time: self.approval_time,
                }
            }

            async fn update_progress(
                ctx: &mut WorkflowContext<Self>,
                progress: u64,
                sleep: u64,
            ) -> () {
                Self::update_progress_status(ctx, progress, sleep, TransferState::Running)
                    .await;
            }

            async fn update_progress_status(
                ctx: &mut WorkflowContext<Self>,
                progress: u64,
                sleep: u64,
                transfer_state: TransferState,
            ) -> () {
                ctx.state_mut(|s| {
                    s.progress = progress;
                    s.transfer_state = transfer_state;
                });

                if sleep > 0 {
                    ctx.timer(TimerOptions {
                        duration: Duration::from_secs(sleep),
                        summary: Some("update progress timer".into()),
                    })
                    .await;
                };
            }
        }
    };
}

// One registered workflow type per scenario the UI can start. All share the body above and
// branch on their own `workflow_type` at runtime.

account_transfer_scenario!(
    AccountTransferHumanInLoop,
    "AccountTransferWorkflowHumanInLoop"
);
account_transfer_scenario!(
    AccountTransferAdvancedVisibility,
    "AccountTransferWorkflowAdvancedVisibility"
);
account_transfer_scenario!(
    AccountTransferRecoverableFailure,
    "AccountTransferWorkflowRecoverableFailure"
);
account_transfer_scenario!(
    AccountTransferApiDowntime,
    "AccountTransferWorkflowAPIDowntime"
);
account_transfer_scenario!(
    AccountTransferInvalidAccount,
    "AccountTransferWorkflowInvalidAccount"
);
