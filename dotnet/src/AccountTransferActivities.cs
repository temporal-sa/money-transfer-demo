using System.Diagnostics;
using Microsoft.Extensions.Logging;
using Temporalio.Activities;
using Temporalio.Exceptions;
using Temporalio.Workflows;

namespace MoneyTransfer;

public class AccountTransferActivities
{
    public static readonly ActivityOptions options = new()
    {
        StartToCloseTimeout = TimeSpan.FromSeconds(5),
        RetryPolicy = new()
        {
            InitialInterval = TimeSpan.FromSeconds(1),
            MaximumInterval = TimeSpan.FromSeconds(30),
            BackoffCoefficient = 2
        }
    };

    private static readonly String API_DOWNTIME = "AccountTransferWorkflowAPIDowntime";
    private static readonly String INVALID_ACCOUNT = "AccountTransferWorkflowInvalidAccount";

    [Activity]
    public async Task<string> ValidateAsync(TransferInput input)
    {
        var logger = ActivityExecutionContext.Current.Logger;
        logger.LogInformation("Validate activity started, input = {}", input);

        // simulate external API call
        _ = await SimulateExternalOperationAsync(1000);

        return "SUCCESS";
    }


    [Activity]
    public async Task<string> WithdrawAsync(ActivityInput input)
    {
        var logger = ActivityExecutionContext.Current.Logger;
        logger.LogInformation("Withdraw activity started, amount = {}", input.Amount);
        int attempt = ActivityExecutionContext.Current.Info.Attempt;

        // simulate external API call
        string error = await SimulateExternalOperationAsync(1000, input.Type, attempt);
        logger.LogInformation("Withdraw call complete, type = {}, error = {}", input.Type, error);

        if (API_DOWNTIME == error)
        {
            // a transient error, which can be retried
            logger.LogInformation("Withdraw API unavailable, attempt = {}", attempt);
            throw new Exception("Withdraw activity failed, API unavailable");
        }

        return "SUCCESS";
    }

    [Activity]
    public async Task<DepositResponse> DepositAsync(ActivityInput input)
    {
        var logger = ActivityExecutionContext.Current.Logger;
        logger.LogInformation("Deposit activity started, amount = {}", input.Amount);
        int attempt = ActivityExecutionContext.Current.Info.Attempt;

        // simulate external API call
        string error = await SimulateExternalOperationAsync(1000, input.Type, attempt);
        logger.LogInformation("Deposit call complete, type = {}, error = {}", input.Type, error);

        if (INVALID_ACCOUNT == error)
        {
            // a business error, which cannot be retried
            throw new ApplicationFailureException("Deposit activity failed, account is invalid", nonRetryable: true);
        }

        return new DepositResponse("example-transfer-id");
    }

    [Activity]
    public async Task<string> SendNotificationAsync(TransferInput input)
    {
        var logger = ActivityExecutionContext.Current.Logger;
        logger.LogInformation("Send notification activity started, input = {}", input);

        // simulate external API call
        _ = await SimulateExternalOperationAsync(1000);

        return "SUCCESS";
    }


    [Activity]
    public async Task<bool> UndoWithdrawAsync(float amount)
    {
        var logger = ActivityExecutionContext.Current.Logger;
        logger.LogInformation("Undo withdraw activity started, amount = {}", amount);

        // simulate external API call
        _ = await SimulateExternalOperationAsync(1000);

        return true;
    }

    private static async Task<string> SimulateExternalOperationAsync(int ms)
    {
        await Task.Delay(ms);
        return "SUCCESS";
    }

    private static async Task<string> SimulateExternalOperationAsync(int ms, String type, int attempt)
    {
        _ = await SimulateExternalOperationAsync(ms / attempt);
        return (attempt < 5) ? type : "NoError";
    }
}
