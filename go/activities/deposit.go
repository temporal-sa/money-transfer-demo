package activities

import (
	"context"
	"errors"
	"money-transfer-worker/app"

	"go.temporal.io/sdk/activity"
	"go.temporal.io/sdk/temporal"
)

const (
	INVALID_ACCOUNT = "AccountTransferWorkflowInvalidAccount"
)

func Deposit(ctx context.Context, input app.ActivityInput) (app.DepositResponse, error) {
	logger := activity.GetLogger(ctx)
	logger.Info("Deposit activity started", "amount", input.Amount)
	attempt := activity.GetInfo(ctx).Attempt

	// simulate external API call
	error := simulateExternalOperationWithError(1000, input.Name, attempt)
	logger.Info("Deposit call complete", "name", input.Name, "error", error)

	if INVALID_ACCOUNT == error {
		// a business error, which cannot be retried
		return app.DepositResponse{},
			temporal.NewNonRetryableApplicationError("deposity activity failed, account is invalid", "activityFailure", errors.New("account invalid"))
	}

	response := app.DepositResponse{
		DepositId: "example-transfer-id",
	}

	return response, nil
}
