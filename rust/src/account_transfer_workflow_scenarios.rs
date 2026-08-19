#![allow(unreachable_pub)]
use std::time::Duration;

use temporalio_common::search_attributes::SearchAttributeKey;
use temporalio_macros::{workflow, workflow_methods};
use temporalio_sdk::{
    ActivityOptions, ApplicationFailure, SyncWorkflowContext, TimerOptions, WorkflowContext,
    WorkflowContextView, WorkflowResult, WorkflowTermination,
};
use tracing::{error, info, warn};

use crate::activities::AccountTransferActivities;
use crate::shared::{
    API_DOWNTIME, ActivityInput, DepositResponse, INVALID_ACCOUNT, TransferInput, TransferOutput,
    TransferState, TransferStatus,
};

const BUG: &str = "AccountTransferWorkflowRecoverableFailure";
const NEEDS_APPROVAL: &str = "AccountTransferWorkflowHumanInLoop";
const ADVANCED_VISIBILITY: &str = "AccountTransferWorkflowAdvancedVisibility";
const SEARCH_ATTRIBUTE: SearchAttributeKey<String> = SearchAttributeKey::keyword("Step");

#[derive(Debug, serde::Serialize, serde::Deserialize)]
struct ScenarioState {
    progress: u64,
    deposit_response: DepositResponse,
    transfer_state: TransferState,
    approval_time: u64,
    approved: bool,
}

impl ScenarioState {
    fn new() -> Self {
        Self {
            progress: 0,
            deposit_response: DepositResponse::default(),
            transfer_state: TransferState::NoneType,
            approval_time: 30,
            approved: false,
        }
    }
}

trait HasScenarioState: Sized + 'static {
    fn scenario_state(&self) -> &ScenarioState;
    fn scenario_state_mut(&mut self) -> &mut ScenarioState;
}

fn handle_approve_transfer_signal<W: HasScenarioState>(
    workflow: &mut W,
    _ctx: &mut SyncWorkflowContext<W>,
) {
    info!("Approve Signal Received");
    let state = workflow.scenario_state_mut();
    if state.transfer_state == TransferState::Waiting {
        state.approved = true;
    } else {
        info!("Approval not applied. Transfer is not waiting for approval");
    }
}

fn handle_approve_transfer_update<W: HasScenarioState>(
    workflow: &mut W,
    _ctx: &mut SyncWorkflowContext<W>,
) -> String {
    info!("Approve Update Validated: Approving Transfer");
    workflow.scenario_state_mut().approved = true;
    "successfully approved transfer".to_string()
}

fn validate_approve_transfer_update<W: HasScenarioState>(
    workflow: &W,
    _ctx: &WorkflowContextView,
    _input: &(),
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    info!("Approve Update Received: Validating");
    let state = workflow.scenario_state();
    if state.approved {
        return Err("Validation Failed: Transfer already approved".into());
    }
    if state.transfer_state != TransferState::Waiting {
        return Err("Validation Failed: Transfer doesn't require approval".into());
    }
    Ok(())
}

fn handle_transfer_status_query<W: HasScenarioState>(
    workflow: &W,
    _ctx: &WorkflowContextView,
) -> TransferStatus {
    let state = workflow.scenario_state();
    TransferStatus {
        progress_percentage: state.progress,
        transfer_state: state.transfer_state.to_string(),
        workflow_status: String::new(),
        charge_result: state.deposit_response.clone(),
        approval_time: state.approval_time,
    }
}

async fn run_scenario<W: HasScenarioState>(
    ctx: &mut WorkflowContext<W>,
    input: TransferInput,
) -> WorkflowResult<TransferOutput> {
    let workflow_type = ctx.info().workflow_type().to_string();
    info!(
        "Dynamic Account Transfer Workflow started {:?}, input = {:?}",
        workflow_type, input
    );

    // Generate the idempotency key within workflow context.
    let idempotency_key = ctx.uuid4();
    info!("Idempotency key set to {idempotency_key}");

    let activity_input = ActivityInput {
        idempotency_key,
        amount: input.amount.into(),
        workflow_type,
    };

    // Validate
    upsert_step(ctx, "Validate").await;
    ctx.execute_activity(
        AccountTransferActivities::validate,
        input.clone(),
        ActivityOptions::start_to_close_timeout(Duration::from_secs(30)),
    )
    .await?;
    update_progress(ctx, 25, 1).await;

    if activity_input.workflow_type == NEEDS_APPROVAL {
        let info = ctx.info();
        info!(
            "Waiting on 'approveTransfer' Signal or Update for workflow ID: {:?}",
            info.workflow_id()
        );
        update_progress_status(ctx, 30, 0, TransferState::Waiting).await;

        // Wait for approval for up to approval_time seconds.
        let approval_time = ctx.state(|workflow| workflow.scenario_state().approval_time);
        let approved = temporalio_sdk::workflows::select! {
            _ = ctx.timer(Duration::from_secs(approval_time)) => false,
            _ = ctx.wait_condition(|workflow: &W| workflow.scenario_state().approved) => true,
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

    // Withdraw
    upsert_step(ctx, "Withdraw").await;
    ctx.execute_activity(
        AccountTransferActivities::withdraw,
        activity_input.clone(),
        ActivityOptions::start_to_close_timeout(Duration::from_secs(30)),
    )
    .await?;
    update_progress(ctx, 50, 3).await;

    // Recoverable-failure scenario: a panic fails the workflow task, not the workflow.
    if activity_input.workflow_type == BUG {
        // BUG: comment out the next two lines and uncomment the info! statement line.
        error!("There's a bug!");
        panic!("Simulated bug - fix me!");
        // info!("Bug is fixed!");
    }

    // Deposit
    upsert_step(ctx, "Deposit").await;
    let deposit_response = match ctx
        .execute_activity(
            AccountTransferActivities::deposit,
            activity_input,
            ActivityOptions::start_to_close_timeout(Duration::from_secs(30)),
        )
        .await
    {
        Ok(response) => response,
        Err(error) => {
            // Deposit failed unrecoverably: roll back the withdraw (saga compensation), then fail
            // the workflow non-retryably.
            warn!("Deposit failed unrecoverable error, reverting withdraw");
            ctx.execute_activity(
                AccountTransferActivities::undo_withdraw,
                "reverting withdraw".to_string(),
                ActivityOptions::start_to_close_timeout(Duration::from_secs(30)),
            )
            .await?;
            return Err(WorkflowTermination::failed_application(
                ApplicationFailure::builder(anyhow::anyhow!("Deposit failed: {error}"))
                    .type_name("DepositFailed".to_string())
                    .non_retryable(true)
                    .build(),
            ));
        }
    };
    info!("after deposit {deposit_response:?}");
    ctx.state_mut(|workflow| {
        workflow.scenario_state_mut().deposit_response = DepositResponse {
            charge_id: deposit_response,
        };
    });
    update_progress(ctx, 75, 1).await;

    // Notification
    upsert_step(ctx, "Notify").await;
    let notification_response = ctx
        .execute_activity(
            AccountTransferActivities::send_notification,
            input,
            ActivityOptions::start_to_close_timeout(Duration::from_secs(30)),
        )
        .await?;
    info!("notification response {notification_response:?}");
    update_progress_status(ctx, 100, 1, TransferState::Finished).await;

    let results = TransferOutput {
        deposit_response: ctx
            .state(|workflow| workflow.scenario_state().deposit_response.charge_id.clone()),
    };
    info!("Returning {results:?}");
    Ok(results)
}

async fn upsert_step<W>(ctx: &mut WorkflowContext<W>, step: &str) {
    let advanced = ctx.info().workflow_type() == ADVANCED_VISIBILITY;
    if advanced {
        info!("Advanced visibility... On step: {step}");
        ctx.upsert_search_attributes([SEARCH_ATTRIBUTE.value_set(step.to_string())]);
    }
}

async fn update_progress<W: HasScenarioState>(
    ctx: &mut WorkflowContext<W>,
    progress: u64,
    sleep: u64,
) {
    update_progress_status(ctx, progress, sleep, TransferState::Running).await;
}

async fn update_progress_status<W: HasScenarioState>(
    ctx: &mut WorkflowContext<W>,
    progress: u64,
    sleep: u64,
    transfer_state: TransferState,
) {
    ctx.state_mut(|workflow| {
        let state = workflow.scenario_state_mut();
        state.progress = progress;
        state.transfer_state = transfer_state;
    });

    if sleep > 0 {
        ctx.timer(
            TimerOptions::builder(Duration::from_secs(sleep))
                .summary("update progress timer".into())
                .build(),
        )
        .await;
    }
}

// The SDK still requires one concrete workflow implementation per registered workflow type. Keep
// only that registration and annotated handler glue in the macro; all behavior above is ordinary
// Rust and is type-checked once.
macro_rules! define_account_transfer_scenario {
    ($workflow:ident, $workflow_type:expr) => {
        #[derive(Debug, serde::Serialize, serde::Deserialize)]
        #[workflow]
        pub struct $workflow {
            state: ScenarioState,
        }

        impl HasScenarioState for $workflow {
            fn scenario_state(&self) -> &ScenarioState {
                &self.state
            }

            fn scenario_state_mut(&mut self) -> &mut ScenarioState {
                &mut self.state
            }
        }

        #[workflow_methods]
        impl $workflow {
            #[init]
            fn new(_ctx: &WorkflowContextView) -> Self {
                Self {
                    state: ScenarioState::new(),
                }
            }

            #[run(name = $workflow_type)]
            pub async fn run(
                ctx: &mut WorkflowContext<Self>,
                input: TransferInput,
            ) -> WorkflowResult<TransferOutput> {
                run_scenario(ctx, input).await
            }

            #[signal(name = "approveTransfer")]
            pub fn approve_transfer_signal(&mut self, ctx: &mut SyncWorkflowContext<Self>) {
                handle_approve_transfer_signal(self, ctx);
            }

            #[update(name = "approveTransferUpdate")]
            pub fn approve_transfer_update(
                &mut self,
                ctx: &mut SyncWorkflowContext<Self>,
            ) -> String {
                handle_approve_transfer_update(self, ctx)
            }

            #[update_validator(approve_transfer_update)]
            fn approve_transfer_update_validator(
                &self,
                ctx: &WorkflowContextView,
                input: &(),
            ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
                validate_approve_transfer_update(self, ctx, input)
            }

            #[query(name = "transferStatus")]
            pub fn query_transfer_status(&self, ctx: &WorkflowContextView) -> TransferStatus {
                handle_transfer_status_query(self, ctx)
            }
        }
    };
}

define_account_transfer_scenario!(AccountTransferHumanInLoop, NEEDS_APPROVAL);
define_account_transfer_scenario!(AccountTransferAdvancedVisibility, ADVANCED_VISIBILITY);
define_account_transfer_scenario!(AccountTransferRecoverableFailure, BUG);
define_account_transfer_scenario!(AccountTransferApiDowntime, API_DOWNTIME);
define_account_transfer_scenario!(AccountTransferInvalidAccount, INVALID_ACCOUNT);
