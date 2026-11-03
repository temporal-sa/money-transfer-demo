package io.temporal.samples.moneytransfer.activities;

import io.temporal.activity.Activity;
import io.temporal.activity.ActivityExecutionContext;
import io.temporal.failure.ApplicationFailure;
import io.temporal.samples.moneytransfer.model.DepositResponse;
import io.temporal.samples.moneytransfer.model.TransferInput;
import lombok.extern.slf4j.Slf4j;

import java.util.concurrent.TimeUnit;

@Slf4j
public class AccountTransferActivitiesImpl implements AccountTransferActivities {

    private static final String API_DOWNTIME = "AccountTransferWorkflowAPIDowntime";
    private static final String INVALID_ACCOUNT = "AccountTransferWorkflowInvalidAccount";
    private static final int DEPOSIT_BATCHES = 6;

    private static void simulateExternalOperation(long ms) {
        try {
            TimeUnit.MILLISECONDS.sleep(ms);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }

    private static String simulateExternalOperation(long ms, String type, int attempt) {
        simulateExternalOperation(ms / attempt);
        return (attempt < 5) ? type : "NoError";
    }

    @Override
    public String validate(TransferInput input) {
        log.info("Validate activity started, input = {}", input);

        // simulate external API call
        simulateExternalOperation(1000);

        return "SUCCESS";
    }

    @Override
    public String withdraw(String idempotencyKey, float amount, String type) {
        log.info("Withdraw activity started, amount = {}", amount);
        int attempt = Activity.getExecutionContext().getInfo().getAttempt();

        // simulate external API call
        String error = simulateExternalOperation(1000, type, attempt);
        log.info("Withdraw call complete, type = {}, error = {}", type, error);

        if (API_DOWNTIME.equals(error)) {
            // a transient error, which can be retried
            log.info("Withdraw API unavailable, attempt = {}", attempt);
            throw new RuntimeException("Withdraw activity failed, API unavailable");
        }

        return "SUCCESS";
    }

    @Override
    public DepositResponse deposit(String idempotencyKey, float amount, String type) {
        log.info("Deposit activity started, amount = {}", amount);
        ActivityExecutionContext ctx = Activity.getExecutionContext();
        int attempt = ctx.getInfo().getAttempt();

        // simulate external API call
        String error = simulateExternalOperation(1000, type, attempt);
        log.info("Deposit call complete, type = {}, error = {}", type, error);

        if (INVALID_ACCOUNT.equals(error)) {
            // a business error, which cannot be retried
            throw ApplicationFailure.newNonRetryableFailure(
                    "Deposit activity failed, account is invalid",
                    "InvalidAccount"
            );
        }

        // Post the deposit in batches, checking in with Temporal after each one.
        // If the Worker dies, the retry picks up after the last batch it reported, not from the start.
        int done = ctx.getHeartbeatDetails(Integer.class).orElse(0);
        if (done > 0) {
            log.info("Deposit resuming after batch {} of {}", done, DEPOSIT_BATCHES);
        }
        for (int batch = done + 1; batch <= DEPOSIT_BATCHES; batch++) {
            simulateExternalOperation(1500);
            ctx.heartbeat(batch);
            log.info("Deposit batch {} of {} posted", batch, DEPOSIT_BATCHES);
        }

        return new DepositResponse("example-transfer-id");
    }

    @Override
    public String sendNotification(TransferInput input) {
        log.info("Send notification activity started, input = {}", input);

        // simulate external API call
        simulateExternalOperation(1000);

        return "SUCCESS";
    }

    @Override
    public boolean undoWithdraw(float amount) {
        log.info("Undo withdraw activity started, amount = {}", amount);

        // simulate external API call
        simulateExternalOperation(1000);

        return true;
    }
}
