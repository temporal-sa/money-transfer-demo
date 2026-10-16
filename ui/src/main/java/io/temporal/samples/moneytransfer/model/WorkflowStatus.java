package io.temporal.samples.moneytransfer.model;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class WorkflowStatus {
    private String workflowId;
    private String workflowStatus;
    private String url;
    private String scenario;
}
