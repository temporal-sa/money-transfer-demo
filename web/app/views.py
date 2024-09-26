async def get_transfer_money_form() -> dict:
    return {

        'scenarios': [
            {'id': 'HAPPY_PATH', 'label': 'Normal "Happy Path" Execution'},
            {'id': "HUMAN_IN_LOOP", 'label': "Require Human-In-Loop Approval"},
            {'id': "API_DOWNTIME", 'label': "API Downtime (recover on 5th attempt)"},
            {'id': "BUG_IN_WORKFLOW", 'label': "Bug in Workflow (recoverable failure)",},
            {'id': "INVALID_ACCOUNT", 'label': "Invalid Account (unrecoverable failure)",},
        ],
        'account_types': [
            {'id': 'checking', 'label': 'Checking'},
            {'id': 'savings', 'label': 'Savings'}
        ],
        'eligible_recipients': [
            {'id': 'justine_morris', 'label': 'Justine Morris'},
            {'id': 'ian_wu', 'label': 'Ian Wu'},
            {'id': 'raul_ruidíaz', 'label': 'Raul Ruidíaz'},
            {'id': 'emma_stockton', 'label': 'Emma Stockton'},
        ]
    }
