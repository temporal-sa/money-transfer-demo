package activities

import (
	"context"
	"errors"
	"money-transfer-worker/app"

	"go.temporal.io/sdk/activity"
)

const (
	API_DOWNTIME = "AccountTransferWorkflowAPIDowntime"
)

func Withdraw(ctx context.Context, input app.ActivityInput) (string, error) {
	logger := activity.GetLogger(ctx)
	logger.Info("Withdraw activity started", "amount", input.Amount)
	attempt := activity.GetInfo(ctx).Attempt

	// simulate external API call
	error := simulateExternalOperationWithError(1000, input.Name, attempt)
	logger.Info("Withdraw call complete", "name", input.Name, "error", error)

	if API_DOWNTIME == error {
		// a transient error, which can be retried
		logger.Info("Withdraw API unavailable", "attempt", attempt)
		return "", errors.New("withdraw activity failed, API unavailable")
	}

	return "SUCCESS", nil
}

func UndoWithdraw(ctx context.Context, amount float32) (bool, error) {
	logger := activity.GetLogger(ctx)
	logger.Info("Undo Withdraw activity started", "amount", amount)

	// simulate external API call
	simulateExternalOperation(1000)

	return true, nil
}
