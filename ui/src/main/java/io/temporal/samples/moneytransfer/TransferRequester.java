package io.temporal.samples.moneytransfer;

import io.temporal.api.common.v1.WorkflowExecution;
import io.temporal.api.workflowservice.v1.DescribeWorkflowExecutionRequest;
import io.temporal.api.workflowservice.v1.DescribeWorkflowExecutionResponse;
import io.temporal.api.workflowservice.v1.WorkflowServiceGrpc;
import io.temporal.client.WorkflowClient;
import io.temporal.client.WorkflowOptions;
import io.temporal.client.WorkflowStub;
import io.temporal.samples.moneytransfer.helper.ServerInfo;
import io.temporal.samples.moneytransfer.model.ExecutionScenario;
import io.temporal.samples.moneytransfer.model.TransferInput;
import io.temporal.samples.moneytransfer.model.TransferOutput;
import io.temporal.samples.moneytransfer.model.TransferStatus;
import io.temporal.serviceclient.WorkflowServiceStubs;

import javax.net.ssl.SSLException;
import java.io.FileNotFoundException;

import static io.temporal.samples.moneytransfer.TemporalClient.getWorkflowServiceStubsWithHeaders;

public class TransferRequester {

    public static TransferOutput getWorkflowOutcome(String workflowId) throws FileNotFoundException, SSLException {
        WorkflowClient client = TemporalClient.get();
        WorkflowStub workflowStub = client.newUntypedWorkflowStub(workflowId);

        // Returns the result after waiting for the Workflow to complete.
        TransferOutput result = workflowStub.getResult(TransferOutput.class);
        return result;
    }

    public static TransferStatus runQuery(String workflowId) throws FileNotFoundException, SSLException {
        WorkflowClient client = TemporalClient.get();
        System.out.println("Workflow STATUS: " + getWorkflowStatus(workflowId));

        WorkflowStub workflowStub = client.newUntypedWorkflowStub(workflowId);
        TransferStatus result = workflowStub.query("transferStatus", TransferStatus.class);
        if ("WORKFLOW_EXECUTION_STATUS_FAILED".equals(getWorkflowStatus(workflowId))) {
            result.setWorkflowStatus("FAILED");
        }
        return result;
    }

    public static void runApproveSignal(String workflowId) {
        try {
            WorkflowClient client = TemporalClient.get();
            WorkflowStub workflowStub = client.newUntypedWorkflowStub(workflowId);
            workflowStub.signal("approveTransfer");
        } catch (Exception e) {
            System.out.println("Exception: " + e);
        }
    }

    public static String runWorkflow(TransferInput transferInput, ExecutionScenario scenario)
            throws FileNotFoundException, SSLException {
        String referenceNumber = generateReferenceNumber(); // random reference number
        WorkflowClient client = TemporalClient.get();
        final String TASK_QUEUE = ServerInfo.getTaskqueue();
        String workflowType = scenario.getWorkflowType();
        WorkflowOptions options = WorkflowOptions.newBuilder()
                .setWorkflowId(referenceNumber)
                .setTaskQueue(TASK_QUEUE)
                .build();
        WorkflowStub transferWorkflow = client.newUntypedWorkflowStub(workflowType, options);
        transferWorkflow.start(transferInput);
        System.out.printf("\n\nTransfer of $%d requested\n", transferInput.getAmount());
        return referenceNumber;
    }

    @SuppressWarnings("CatchAndPrintStackTrace")
    public static void main(String[] args) throws Exception {
        int amountCents = 45; // amount to transfer
        TransferInput params = new TransferInput(amountCents, "account1", "account2");
        runWorkflow(params, ExecutionScenario.HAPPY_PATH);
        System.exit(0);
    }

    private static String generateReferenceNumber() {
        return String.format(
                "TRANSFER-%s-%03d",
                (char) (Math.random() * 26 + 'A') +
                        "" +
                        (char) (Math.random() * 26 + 'A') +
                        (char) (Math.random() * 26 + 'A'),
                (int) (Math.random() * 999)
        );
    }

    private static String getWorkflowStatus(String workflowId) throws FileNotFoundException, SSLException {
        WorkflowServiceStubs service = getWorkflowServiceStubsWithHeaders();
        WorkflowServiceGrpc.WorkflowServiceBlockingStub stub = service.blockingStub();
        DescribeWorkflowExecutionRequest request = DescribeWorkflowExecutionRequest.newBuilder()
                .setNamespace(ServerInfo.getNamespace())
                .setExecution(WorkflowExecution.newBuilder().setWorkflowId(workflowId))
                .build();
        DescribeWorkflowExecutionResponse response = stub.describeWorkflowExecution(request);
        return response.getWorkflowExecutionInfo().getStatus().name();
    }
}
