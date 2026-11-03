package io.temporal.samples.moneytransfer.workflows;

import io.temporal.common.SearchAttributeKey;
import io.temporal.common.converter.EncodedValues;
import io.temporal.failure.ActivityFailure;
import io.temporal.failure.ApplicationFailure;
import io.temporal.samples.moneytransfer.activities.AccountTransferActivities;
import io.temporal.samples.moneytransfer.model.DepositResponse;
import io.temporal.samples.moneytransfer.model.TransferInput;
import io.temporal.samples.moneytransfer.model.TransferOutput;
import io.temporal.samples.moneytransfer.model.TransferStatus;
import io.temporal.workflow.DynamicWorkflow;
import io.temporal.workflow.Workflow;
import java.time.Duration;
import org.slf4j.Logger;

public class AccountTransferWorkflowScenarios implements DynamicWorkflow {

    private static final String BUG = "AccountTransferWorkflowRecoverableFailure";
    private static final String NEEDS_APPROVAL = "AccountTransferWorkflowHumanInLoop";
    private static final String ADVANCED_VISIBILITY = "AccountTransferWorkflowAdvancedVisibility";

    private static final Logger log = Workflow.getLogger(AccountTransferWorkflowScenarios.class);

    private final SearchAttributeKey<String> WORKFLOW_STEP = SearchAttributeKey.forKeyword("Step");

    private final AccountTransferActivities activities = Workflow.newActivityStub(
        AccountTransferActivities.class,
        AccountTransferActivities.activityOptions
    );

    private final AccountTransferActivities depositActivities = Workflow.newActivityStub(
        AccountTransferActivities.class,
        AccountTransferActivities.activityOptions.toBuilder()
            .setStartToCloseTimeout(Duration.ofSeconds(30))
            .setHeartbeatTimeout(Duration.ofSeconds(5))
            .build()
    );

    private int progress = 0;
    private String transferState = "starting";
    private DepositResponse depositResponse = new DepositResponse("");

    private int approvalTime = 30;
    private boolean approved = false;

    @Override
    public Object execute(EncodedValues args) {
        Workflow.registerListener(new AccountTransferDynamicListenerImpl());
        TransferInput input = args.get(0, TransferInput.class);
        String type = Workflow.getInfo().getWorkflowType();
        log.info("Dynamic Account Transfer workflow started, type = {}", type);
        String idempotencyKey = Workflow.randomUUID().toString();

        // Validate
        upsertStep("Validate");
        activities.validate(input);
        updateProgress(25, 1);

        if (NEEDS_APPROVAL.equals(type)) {
            log.info(
                "Waiting on 'approveTransfer' Signal or Update for workflow ID: {}",
                Workflow.getInfo().getWorkflowId()
            );
            updateProgress(30, 0, "waiting");

            // Wait for the approval for up to approvalTime
            boolean receivedApproval = Workflow.await(Duration.ofSeconds(approvalTime), () -> approved);

            // If the approval was not received within the timeout, fail the workflow
            if (!receivedApproval) {
                log.error(
                    "Approval not received within the {}-second time window: Failing the workflow.",
                    approvalTime
                );
                throw ApplicationFailure.newFailure(
                    "Approval not received within " + approvalTime + " seconds",
                    "ApprovalTimeout"
                );
            }
        }

        // Withdraw
        upsertStep("Withdraw");
        activities.withdraw(idempotencyKey, input.getAmount(), type);
        updateProgress(50, 3);

        if (BUG.equals(type)) {
            // Simulate bug
            throw new RuntimeException("Simulated bug - fix me!");
        }

        // Deposit
        upsertStep("Deposit");
        try {
            depositResponse = depositActivities.deposit(idempotencyKey, input.getAmount(), type);
            updateProgress(75, 1);
        } catch (ActivityFailure e) {
            // if deposit fails in an unrecoverable way, rollback the withdrawal and fail the workflow
            log.info("Deposit failed unrecoverable error, reverting withdraw");

            // Undo Withdraw (rollback)
            activities.undoWithdraw(input.getAmount());

            // return failure message
            String message = ((ApplicationFailure) e.getCause()).getOriginalMessage();
            throw ApplicationFailure.newNonRetryableFailure(message, "DepositFailed");
        }

        // Send Notification
        upsertStep("Send Notification");
        activities.sendNotification(input);
        updateProgress(100, 1, "finished");

        return new TransferOutput(depositResponse);
    }

    private void upsertStep(String step) {
        if (ADVANCED_VISIBILITY.equals(Workflow.getInfo().getWorkflowType())) {
            log.info("Advanced visibility .. {}", step);
            Workflow.upsertTypedSearchAttributes(WORKFLOW_STEP.valueSet(step));
        }
    }

    private void updateProgress(int progress, int sleep) {
        updateProgress(progress, sleep, "running");
    }

    private void updateProgress(int progress, int sleep, String transferState) {
        if (sleep > 0) {
            Workflow.sleep(Duration.ofSeconds(sleep));
        }
        this.transferState = transferState;
        this.progress = progress;
    }

    class AccountTransferDynamicListenerImpl implements AccountTransferMessages {

        @Override
        public TransferStatus queryTransferStatus() {
            return new TransferStatus(progress, transferState, "", depositResponse, approvalTime);
        }

        @Override
        public void approveTransferSignal() {
            log.info("Approve Signal Received");

            if (transferState.equals("waiting")) {
                approved = true;
            } else {
                log.info("Signal not applied: Transfer is not waiting for approval.");
            }
        }

        @Override
        public String approveTransferUpdate() {
            log.info("Approve Update Validated: Approving Transfer");
            approved = true;
            return "successfully approved transfer";
        }

        @Override
        public void approveTransferUpdateValidator() {
            log.info("Approve Update Received: Validating");
            if (approved) {
                throw new IllegalStateException("Validation Failed: Transfer already approved");
            }
            if (!transferState.equals("waiting")) {
                throw new IllegalStateException("Validation Failed: Transfer doesn't require approval");
            }
        }
    }
}
