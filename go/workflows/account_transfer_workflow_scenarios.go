package workflows

import (
	"fmt"
	"money-transfer-worker/activities"
	"money-transfer-worker/app"
	"money-transfer-worker/messages"
	"time"

	"github.com/google/uuid"
	"go.temporal.io/sdk/temporal"
	"go.temporal.io/sdk/workflow"
)

const (
	ADVANCED_VISIBILTY = "AccountTransferWorkflowAdvancedVisibility"
	NEEDS_APPROVAL     = "AccountTransferWorkflowHumanInLoop"
	BUG                = "AccountTransferWorkflowRecoverableFailure"
	APPROVAL_TIME      = 30
)

var stepKey = temporal.NewSearchAttributeKeyKeyword("Step")

func AccountTransferWorkflowScenarios(ctx workflow.Context, input app.TransferInput) (output *app.TransferOutput, err error) {
	name := workflow.GetInfo(ctx).WorkflowType.Name
	logger := workflow.GetLogger(ctx)
	logger.Info("Dynamic Account Transfer workflow started", "name", name)

	activityOptions := workflow.ActivityOptions{
		StartToCloseTimeout: 5 * time.Second,
		RetryPolicy: &temporal.RetryPolicy{
			InitialInterval:    1 * time.Second,
			BackoffCoefficient: 2.0,
			MaximumInterval:    30 * time.Second,
		},
	}
	ctx = workflow.WithActivityOptions(ctx, activityOptions)

	// Expose transfer status as a query
	ts, err := messages.SetQueryHandlerForStatus(ctx)
	if err != nil {
		return nil, err
	}

	var idempotencyKey string
	_ = workflow.SideEffect(ctx, func(ctx workflow.Context) interface{} {
		return uuid.New().String()
	}).Get(&idempotencyKey)

	// Validate
	upsertStep(ctx, "Validate")
	err = workflow.ExecuteActivity(ctx, activities.Validate, input).Get(ctx, nil)
	if err != nil {
		return nil, err
	}
	updateProgress(ctx, 1, ts, 25)

	if NEEDS_APPROVAL == name {
		logger.Info("Waiting on 'approveTransfer' Signal or Update for workflow ID: ", workflow.GetInfo(ctx).WorkflowExecution.ID)
		updateProgress(ctx, 0, ts, 30)
		ts.TransferState = "waiting"

		// Wait for the approval for up to approvalTime
		c := messages.GetSignalChannelForApproval(ctx)
		receivedApproval, _ := c.ReceiveWithTimeout(ctx, time.Second*APPROVAL_TIME, nil)

		// If the signal was not received within the timeout, fail the workflow
		if !receivedApproval {
			return nil, fmt.Errorf("approval not received within %d seconds", APPROVAL_TIME)
		}
	}

	// Withdraw
	upsertStep(ctx, "Withdraw")
	err = workflow.ExecuteActivity(ctx, activities.Withdraw, idempotencyKey, input.Amount, name).Get(ctx, nil)
	if err != nil {
		return nil, err
	}
	updateProgress(ctx, 3, ts, 50)

	if BUG == name {
		// Simulate bug
		panic("Simulated bug - fix me!")
	}

	// Deposit
	upsertStep(ctx, "Deposit")
	depositResponse := app.DepositResponse{}
	err = workflow.ExecuteActivity(ctx, activities.Deposit, idempotencyKey, input.Amount, name).Get(ctx, &depositResponse)
	if err != nil {
		// if deposit fails in an unrecoverable way, rollback the withdrawal and fail the workflow
		logger.Info("Deposit failed unrecoverable error, reverting withdraw")

		// Undo Withdraw (rollback)
		workflow.ExecuteActivity(ctx, activities.UndoWithdraw, input.Amount).Get(ctx, nil)

		return nil, fmt.Errorf("deposit failed %w", err)
	}
	updateProgress(ctx, 1, ts, 75)

	// Send Notification
	upsertStep(ctx, "SendNotification")
	err = workflow.ExecuteActivity(ctx, activities.SendNotification, input).Get(ctx, nil)
	if err != nil {
		return nil, err
	}
	updateProgress(ctx, 0, ts, 100)

	output = &app.TransferOutput{
		DepositResponse: depositResponse,
	}
	return output, nil
}

func upsertStep(ctx workflow.Context, step string) {
	if ADVANCED_VISIBILTY == workflow.GetInfo(ctx).WorkflowType.Name {
		workflow.GetLogger(ctx).Info("Advanced visibility ..", "step", step)
		workflow.UpsertTypedSearchAttributes(ctx, stepKey.ValueSet(step))
	}
}
