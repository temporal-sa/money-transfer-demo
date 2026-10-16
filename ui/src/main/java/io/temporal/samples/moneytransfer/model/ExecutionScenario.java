package io.temporal.samples.moneytransfer.model;

public enum ExecutionScenario {
    HAPPY_PATH("AccountTransferWorkflow"),
    ADVANCED_VISIBILITY("AccountTransferWorkflowAdvancedVisibility"),
    HUMAN_IN_LOOP("AccountTransferWorkflowHumanInLoop"),
    API_DOWNTIME("AccountTransferWorkflowAPIDowntime"),
    BUG_IN_WORKFLOW("AccountTransferWorkflowRecoverableFailure"),
    INVALID_ACCOUNT("AccountTransferWorkflowInvalidAccount");

    private final String workflowType;

    ExecutionScenario(String workflowType) {
        this.workflowType = workflowType;
    }

    public String getWorkflowType() {
        return this.workflowType;
    }

    // The scenario a workflow type runs, or null for a type this UI didn't start
    public static ExecutionScenario fromWorkflowType(String workflowType) {
        for (ExecutionScenario scenario : values()) {
            if (scenario.workflowType.equals(workflowType)) {
                return scenario;
            }
        }
        return null;
    }
}
