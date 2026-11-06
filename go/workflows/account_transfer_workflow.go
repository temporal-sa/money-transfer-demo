package workflows

import (
	"money-transfer-worker/activities"
	"money-transfer-worker/app"
	"money-transfer-worker/messages"
	"time"

	"github.com/google/uuid"
	"go.temporal.io/sdk/temporal"
	"go.temporal.io/sdk/workflow"
)

func AccountTransferWorkflow(ctx workflow.Context, input app.TransferInput) (output *app.TransferOutput, err error) {
	name := workflow.GetInfo(ctx).WorkflowType.Name
	logger := workflow.GetLogger(ctx)
	logger.Info("Account Transfer workflow started", "name", name)

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
	err = workflow.ExecuteActivity(ctx, activities.Validate, input).Get(ctx, nil)
	if err != nil {
		return nil, err
	}
	updateProgress(ctx, 1, ts, 25)

	// Withdraw
	err = workflow.ExecuteActivity(ctx, activities.Withdraw, idempotencyKey, input.Amount, name).Get(ctx, nil)
	if err != nil {
		return nil, err
	}
	updateProgress(ctx, 3, ts, 50)

	// Deposit
	depositResponse := app.DepositResponse{}
	err = workflow.ExecuteActivity(ctx, activities.Deposit, idempotencyKey, input.Amount, name).Get(ctx, &depositResponse)
	if err != nil {
		return nil, err
	}
	updateProgress(ctx, 1, ts, 75)

	// Send Notification
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

func updateProgress(ctx workflow.Context, sleep int, ts *app.TransferStatus, progress int) {
	if sleep > 0 {
		duration := time.Duration(sleep) * time.Second
		workflow.Sleep(ctx, duration)
	}
	state := "running"
	if progress == 100 {
		state = "finished"
	}
	ts.TransferState = state
	ts.ProgressPercentage = progress
}
