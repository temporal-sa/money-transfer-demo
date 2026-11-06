package io.temporal.samples.moneytransfer.workflows;

import io.temporal.samples.moneytransfer.activities.AccountTransferActivities;
import io.temporal.samples.moneytransfer.model.DepositResponse;
import io.temporal.samples.moneytransfer.model.TransferInput;
import io.temporal.samples.moneytransfer.model.TransferOutput;
import io.temporal.samples.moneytransfer.model.TransferStatus;
import io.temporal.workflow.Workflow;
import org.slf4j.Logger;

import java.time.Duration;

public class AccountTransferWorkflowImpl implements AccountTransferWorkflow {

    private static final Logger log = Workflow.getLogger(AccountTransferWorkflowImpl.class);

    private final AccountTransferActivities activities = Workflow.newActivityStub(
            AccountTransferActivities.class,
            AccountTransferActivities.activityOptions
    );

    private int progress = 0;
    private String transferState = "starting";
    private DepositResponse depositResponse = new DepositResponse("");

    @Override
    public TransferOutput transfer(TransferInput input) {
        String type = Workflow.getInfo().getWorkflowType();
        log.info("Account Transfer workflow started, type = {}", type);
        String idempotencyKey = Workflow.randomUUID().toString();

        // Validate
        activities.validate(input);
        updateProgress(25, 1);

        // Withdraw
        activities.withdraw(idempotencyKey, input.getAmount(), type);
        updateProgress(50, 3);

        // Deposit
        depositResponse = activities.deposit(idempotencyKey, input.getAmount(), type);
        updateProgress(75, 1);

        // Send Notification
        activities.sendNotification(input);
        updateProgress(100, 0, "finished");

        return new TransferOutput(depositResponse);
    }

    @Override
    public TransferStatus queryTransferStatus() {
        return new TransferStatus(progress, transferState, "", depositResponse, 0);
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
}
