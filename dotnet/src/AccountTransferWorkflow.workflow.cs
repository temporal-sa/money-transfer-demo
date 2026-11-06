using Microsoft.Extensions.Logging;
using Temporalio.Workflows;

namespace MoneyTransfer;

[Workflow]
public class AccountTransferWorkflow
{
    private int progress = 0;
    private string transferState = "starting";
    private DepositResponse depositResponse = new(string.Empty);

    [WorkflowRun]
    public async Task<TransferOutput> Transfer(TransferInput input)
    {
        var logger = Workflow.Logger;
        var type = Workflow.Info.WorkflowType;
        logger.LogInformation("Account Transfer workflow started, type = {}", type);
        var idempotencyKey = Workflow.Random.Next().ToString();

        // Validate
        await Workflow.ExecuteActivityAsync((AccountTransferActivities act) =>
            act.ValidateAsync(input), AccountTransferActivities.options);
        await UpdateProgressAsync(25, 1);

        // Withdraw
        await Workflow.ExecuteActivityAsync((AccountTransferActivities act) =>
            act.WithdrawAsync(idempotencyKey, input.Amount, type), AccountTransferActivities.options);
        await UpdateProgressAsync(50, 3);

        // Deposit
        depositResponse = await Workflow.ExecuteActivityAsync((AccountTransferActivities act) =>
            act.DepositAsync(idempotencyKey, input.Amount, type), AccountTransferActivities.options);
        await UpdateProgressAsync(75, 1);

        // Send Notification
        await Workflow.ExecuteActivityAsync((AccountTransferActivities act) =>
            act.SendNotificationAsync(input), AccountTransferActivities.options);
        await UpdateProgressAsync(100, 0, "finished");

        return new TransferOutput(depositResponse);
    }

    [WorkflowQuery("transferStatus")]
    public TransferStatus QueryTransferStatus()
    {
        return new TransferStatus(progress, transferState, string.Empty, depositResponse, 0);
    }

    private async Task UpdateProgressAsync(int progress, int sleep) {
        await UpdateProgressAsync(progress, sleep, "running");
    }

    private async Task UpdateProgressAsync(int progress, int sleep, string transferState) {
        if (sleep > 0) {
            await Workflow.DelayAsync(TimeSpan.FromSeconds(sleep));
        }
        this.transferState = transferState;
        this.progress = progress;
    }

}
