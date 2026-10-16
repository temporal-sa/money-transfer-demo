package io.temporal.samples.moneytransfer;

import com.google.common.base.Splitter;
import com.google.protobuf.Timestamp;
import io.grpc.stub.MetadataUtils;
import io.temporal.api.workflow.v1.WorkflowExecutionInfo;
import io.temporal.api.workflowservice.v1.ListWorkflowExecutionsRequest;
import io.temporal.api.workflowservice.v1.ListWorkflowExecutionsResponse;
import io.temporal.client.WorkflowClient;
import io.temporal.client.WorkflowExecutionMetadata;
import io.temporal.samples.moneytransfer.helper.ServerInfo;
import io.temporal.samples.moneytransfer.model.ExecutionScenario;
import io.temporal.samples.moneytransfer.model.WorkflowStatus;
import io.temporal.serviceclient.WorkflowServiceStubs;

import javax.net.ssl.SSLException;
import java.io.FileNotFoundException;
import java.text.SimpleDateFormat;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.List;

import static io.temporal.samples.moneytransfer.TemporalClient.getWorkflowServiceStubs;

public class TransferLister {

    public static List<WorkflowStatus> listWorkflows() throws FileNotFoundException, SSLException {
        WorkflowClient client = TemporalClient.get();

        List<WorkflowExecutionMetadata> responseOpen = client.listExecutions(
                "ExecutionStatus = 'Running'" +
                "AND WorkflowType STARTS_WITH 'AccountTransferWorkflow'" +
                "AND StartTime BETWEEN '" +
                timeStampToString(getOneHourAgo()) +
                "'" +
                " AND '" +
                timeStampToString(getNow()) +
                "'"
            ).toList();

        List<WorkflowExecutionMetadata> responseClosed = client.listExecutions(
        "ExecutionStatus != 'Running'" +
                "AND WorkflowType STARTS_WITH 'AccountTransferWorkflow'" +
                "AND StartTime BETWEEN '" +
                timeStampToString(getOneHourAgo()) +
                "'" +
                " AND '" +
                timeStampToString(getNow()) +
                "'"
            ).toList();

        // array of WorkflowStatus
        List<WorkflowStatus> workflowStatusList = new ArrayList<>();

        for (WorkflowExecutionMetadata workflowExecutionMetadata : responseOpen) {
            WorkflowStatus workflowStatusOpen = new WorkflowStatus();
            workflowStatusOpen.setWorkflowId(workflowExecutionMetadata.getExecution().getWorkflowId());
            workflowStatusOpen.setWorkflowStatus(getWorkflowStatus(workflowExecutionMetadata.getStatus().toString()));
            workflowStatusOpen.setUrl(getWorkflowUrl(workflowExecutionMetadata.getExecution().getWorkflowId()));
            workflowStatusOpen.setScenario(getScenario(workflowExecutionMetadata.getWorkflowType()));
            workflowStatusList.add(workflowStatusOpen);
        }

        for (WorkflowExecutionMetadata workflowExecutionMetadata : responseClosed) {
            WorkflowStatus workflowStatusClosed = new WorkflowStatus();
            workflowStatusClosed.setWorkflowId(workflowExecutionMetadata.getExecution().getWorkflowId());
            workflowStatusClosed.setWorkflowStatus(getWorkflowStatus(workflowExecutionMetadata.getStatus().toString()));
            workflowStatusClosed.setUrl(getWorkflowUrl(workflowExecutionMetadata.getExecution().getWorkflowId()));
            workflowStatusClosed.setScenario(getScenario(workflowExecutionMetadata.getWorkflowType()));
            workflowStatusList.add(workflowStatusClosed);
        }

        return workflowStatusList;
    }

    // in the format the UI expects
    private static String getWorkflowStatus(String input) {
        if (input == null || input.isEmpty()) {
            return ""; // Return empty string if input is null or empty
        }

        List<String> parts = Splitter.on('_').splitToList(input);

        return parts.get(parts.size() - 1); // Return the last part
    }

    private static String timeStampToString(Timestamp aTime) {
        java.sql.Timestamp javaTimestamp = new java.sql.Timestamp(aTime.getSeconds() * 1000);
        return new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSXXX").format(javaTimestamp);
    }

    private static Timestamp getNow() {
        LocalDateTime now = LocalDateTime.now(ZoneId.of("UTC"));
        Instant instant = now.atZone(ZoneId.of("UTC")).toInstant();
        Timestamp timestamp = Timestamp.newBuilder()
                .setSeconds(instant.getEpochSecond())
                .setNanos(instant.getNano())
                .build();

        return timestamp;
    }

    private static Timestamp getOneHourAgo() {
        // Get current date-time in UTC
        LocalDateTime now = LocalDateTime.now(ZoneId.of("UTC"));

        // Subtract one hour
        LocalDateTime oneHourAgo = now.minusHours(1);

        // Convert LocalDateTime to Instant
        Instant instant = oneHourAgo.atZone(ZoneId.of("UTC")).toInstant();

        // Convert Instant to Timestamp
        Timestamp timestamp = Timestamp.newBuilder()
                .setSeconds(instant.getEpochSecond())
                .setNanos(instant.getNano())
                .build();

        return timestamp;
    }

    private static String getScenario(String workflowType) {
        ExecutionScenario scenario = ExecutionScenario.fromWorkflowType(workflowType);
        return scenario == null ? "" : scenario.name();
    }

    private static String getWorkflowUrl(String workflowId) {
        String workflowsUrl = ServerInfo.getWorkflowsUrl();
        return workflowsUrl.isEmpty() ? "" : workflowsUrl + "/" + workflowId;
    }

    public static void main(String[] args) throws FileNotFoundException, SSLException {
        List<WorkflowStatus> workflowStatusList = listWorkflows();
        for (WorkflowStatus workflowStatus : workflowStatusList) {
            System.out.println(
                    workflowStatus.getWorkflowId() +
                            " " +
                            workflowStatus.getWorkflowStatus() +
                            " " +
                            workflowStatus.getUrl()
            );
        }
    }
}
