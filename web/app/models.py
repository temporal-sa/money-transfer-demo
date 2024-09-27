DEFAULT_WORKFLOW_TYPE = 'AccountTransferWorkflow'
SCENARIOS = [
    {'id': DEFAULT_WORKFLOW_TYPE, 'label': 'Normal "Happy Path" Execution'},
    {'id': "AccountTransferWorkflowHumanInLoop", 'label': "Require Human-In-Loop Approval"},
    {'id': "AccountTransferWorkflowAPIDowntime", 'label': "API Downtime (recover on 5th attempt)"},
    {'id': "AccountTransferWorkflowRecoverableFailure", 'label': "Bug in Workflow (recoverable failure)",},
    {'id': "AccountTransferWorkflowInvalidAccount", 'label': "Invalid Account (unrecoverable failure)",},
]

ACCOUNT_TYPES = [
    {'id': 'checking', 'label': 'Checking'},
    {'id': 'savings', 'label': 'Savings'}
]

ELIGIBLE_RECIPIENTS = [
    {'id': 'justine_morris', 'label': 'Justine Morris'},
    {'id': 'ian_wu', 'label': 'Ian Wu'},
    {'id': 'raul_ruidíaz', 'label': 'Raul Ruidíaz'},
    {'id': 'emma_stockton', 'label': 'Emma Stockton'},
]