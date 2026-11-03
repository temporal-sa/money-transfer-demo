package io.temporal.samples.moneytransfer;

import io.temporal.samples.moneytransfer.activities.AccountTransferActivitiesImpl;
import io.temporal.samples.moneytransfer.util.ServerInfo;
import io.temporal.samples.moneytransfer.workflows.AccountTransferWorkflowImpl;
import io.temporal.samples.moneytransfer.workflows.AccountTransferWorkflowScenarios;
import io.temporal.worker.Worker;
import io.temporal.worker.WorkerFactory;
import io.temporal.worker.WorkerOptions;
import java.time.Duration;

public class AccountTransferWorker {

    @SuppressWarnings("CatchAndPrintStackTrace")
    public static void main(String[] args) throws Exception {
        final String TASK_QUEUE = ServerInfo.getTaskqueue();

        WorkerFactory factory = WorkerFactory.newInstance(TemporalClient.get());

        // Send each Deposit heartbeat within a second, so the UI shows the latest batch (the SDK otherwise batches them up)
        Worker worker = factory.newWorker(TASK_QUEUE, WorkerOptions.newBuilder()
                .setMaxHeartbeatThrottleInterval(Duration.ofSeconds(1))
                .build());
        worker.registerWorkflowImplementationTypes(AccountTransferWorkflowImpl.class);
        worker.registerWorkflowImplementationTypes(AccountTransferWorkflowScenarios.class);
        worker.registerActivitiesImplementations(new AccountTransferActivitiesImpl());

        factory.start();
        System.out.println("Worker started for task queue: " + TASK_QUEUE);
    }
}
