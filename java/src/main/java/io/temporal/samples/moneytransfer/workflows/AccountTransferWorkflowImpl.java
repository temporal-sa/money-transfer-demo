package io.temporal.samples.moneytransfer.workflows;

import io.temporal.activity.ActivityOptions;
import io.temporal.common.RetryOptions;
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

    // Withdraw, with every failure-handling option spelled out. All of it is declarative:
    // no try/catch, no retry loop, no sleep. The other three calls get the same behaviour from the
    // shared activityOptions. In Java, options usually go on the stub rather than the call, so Withdraw gets its own stub.
    private final AccountTransferActivities withdrawActivities = Workflow.newActivityStub(
            AccountTransferActivities.class,
            ActivityOptions.newBuilder()
                    // Time to complete, per attempt: if the bank API hangs or the worker dies mid-call,
                    // Temporal gives up on this attempt after 5s and retries it. Always set this one.
                    .setStartToCloseTimeout(Duration.ofSeconds(5))
                    // Time to complete, overall: the whole withdrawal, every retry included, gets 5 minutes.
                    // This, not a count of attempts, is what bounds the retries below.
                    .setScheduleToCloseTimeout(Duration.ofMinutes(5))
                    // Time to start: how long the task may wait in the queue for a worker. Off on purpose:
                    // it is never retried, so a worker outage longer than this would fail the transfer.
                    // .setScheduleToStartTimeout(Duration.ofMinutes(1))
                    // Heartbeats: for long-running work that reports progress, so a lost worker is noticed early.
                    // A withdrawal takes a second, so it doesn't heartbeat.
                    // .setHeartbeatTimeout(Duration.ofSeconds(10))
                    .setRetryOptions(RetryOptions.newBuilder()
                            .setInitialInterval(Duration.ofSeconds(1))  // first retry after 1s
                            .setBackoffCoefficient(2.0)                 // then 2s, 4s, 8s ... backing off the struggling API
                            .setMaximumInterval(Duration.ofSeconds(30)) // but never wait more than 30s between tries
                            .setMaximumAttempts(0)                      // 0 = unlimited; the 5-minute budget is the limit
                            // Errors that retrying can't fix stop at once, e.g. .setDoNotRetry("InsufficientFunds").
                            // Deposit does the same from the other side: it throws newNonRetryableFailure(..., "InvalidAccount").
                            .build())
                    .build()
    );

    // Deposit posts in batches and heartbeats after each one, so it gets its own options too.
    private final AccountTransferActivities depositActivities = Workflow.newActivityStub(
            AccountTransferActivities.class,
            AccountTransferActivities.activityOptions.toBuilder()
                    .setStartToCloseTimeout(Duration.ofSeconds(30))  // six batches
                    .setHeartbeatTimeout(Duration.ofSeconds(5))      // a dead Worker is noticed in 5s, not 30s
                    .build()
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

        // Withdraw: options spelled out on withdrawActivities above
        withdrawActivities.withdraw(idempotencyKey, input.getAmount(), type);
        updateProgress(50, 3);

        // Deposit: heartbeats after each batch (depositActivities above)
        depositResponse = depositActivities.deposit(idempotencyKey, input.getAmount(), type);
        updateProgress(75, 1);

        // Send Notification
        activities.sendNotification(input);
        updateProgress(100, 1, "finished");

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
