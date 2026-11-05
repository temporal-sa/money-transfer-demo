using Microsoft.Extensions.Logging;
using Temporalio.Common;
using Temporalio.Converters;
using Temporalio.Exceptions;
using Temporalio.Workflows;

namespace MoneyTransfer;

[Workflow(Dynamic = true)]
public class AccountTransferWorkflowScenarios
{
    private static readonly string BUG = "AccountTransferWorkflowRecoverableFailure";
    private static readonly string NEEDS_APPROVAL = "AccountTransferWorkflowHumanInLoop";
    private static readonly string ADVANCED_VISIBILITY = "AccountTransferWorkflowAdvancedVisibility";

    private SearchAttributeKey<string> stepAttributKey = SearchAttributeKey.CreateKeyword("Step");

    private int progress = 0;
    private string transferState = "starting";
    private DepositResponse depositResponse = new(string.Empty);

    private int approvalTime = 30;
    private bool approved = false;


    [WorkflowRun]
    public async Task<TransferOutput> RunAsync(IRawValue[] args)
    {
        var logger = Workflow.Logger;
        var type = Workflow.Info.WorkflowType;
        var input = Workflow.PayloadConverter.ToValue<TransferInput>(args[0]);
        logger.LogInformation("Dynamic Account Transfer workflow started, type = {}", type);
        var idempotencyKey = Workflow.Random.Next().ToString();

        // Validate
        UpsertStep("Validate");
        await Workflow.ExecuteActivityAsync((AccountTransferActivities act) =>
            act.ValidateAsync(input), AccountTransferActivities.options);
        await UpdateProgressAsync(25, 1);

        if (NEEDS_APPROVAL == type)
        {
            logger.LogInformation("Waiting on 'approveTransfer' Signal or Update for workflow ID: {}", Workflow.Info.WorkflowId);
            await UpdateProgressAsync(30, 0, "waiting");

            var receivedApproval = await Workflow.WaitConditionAsync(() => approved, TimeSpan.FromSeconds(approvalTime));
            if (!receivedApproval)
            {

                logger.LogInformation("Approval not received within the {}-second time window: Failing the workflow.", approvalTime);
                throw new ApplicationFailureException("Approval not received within " + approvalTime + " seconds");
            }
        }

        // Withdraw
        UpsertStep("Withdraw");
        await Workflow.ExecuteActivityAsync((AccountTransferActivities act) =>
            act.WithdrawAsync(idempotencyKey, input.Amount, type), AccountTransferActivities.options);
        await UpdateProgressAsync(50, 3);

        if (BUG == type)
        {
            // Simulate bug
            throw new Exception("Simulate bug - fix me!");
        }

        // Deposit
        UpsertStep("Deposit");
        try
        {
            depositResponse = await Workflow.ExecuteActivityAsync((AccountTransferActivities act) =>
                    act.DepositAsync(idempotencyKey, input.Amount, type), AccountTransferActivities.options);
            await UpdateProgressAsync(75, 1);
        }
        catch (ActivityFailureException e)
        {
            // if deposit fails in an unrecoverable way, rollback the withdrawal and fail the workflow
            logger.LogInformation("Deposit failed unrecoverable error, reverting withdraw");

            // Undo Withdraw (rollback)
            await Workflow.ExecuteActivityAsync((AccountTransferActivities act) =>
                act.UndoWithdrawAsync(input.Amount), AccountTransferActivities.options);

            // return failure message
            throw new ApplicationFailureException(e.Message);
        }

        // Send Notification
        UpsertStep("Send Notification");
        await Workflow.ExecuteActivityAsync((AccountTransferActivities act) =>
            act.SendNotificationAsync(input), AccountTransferActivities.options);
        await UpdateProgressAsync(100, 0, "finished");

        return new TransferOutput(depositResponse);
    }

    [WorkflowQuery("transferStatus")]
    public TransferStatus QueryTransferStatus()
    {
        return new TransferStatus(progress, transferState, string.Empty, depositResponse, approvalTime);
    }

    [WorkflowSignal("approveTransfer")]
    public async Task ApproveTransferSignal()
    {
        Workflow.Logger.LogInformation("Approve Signal Received");
        if (transferState == "waiting")
        {
            approved = true;
        }
        else
        {
            Workflow.Logger.LogInformation("Signal not applied: Transfer is not waiting for approval");
        }
    }

    [WorkflowUpdate("approveTransferUpdate")]
    public async Task<string> ApproveTransferUpdate()
    {
        Workflow.Logger.LogInformation("Approve Update Validated: Approving Transfer");
        approved = true;
        return "successfully approved transfer";
    }

    [WorkflowUpdateValidator("ApproveTransferUpdate")]
    public void ApproveTransferUpdateValidator()
    {
        Workflow.Logger.LogInformation("Approve Update Received: Validating");
        if (approved)
        {
            throw new InvalidOperationException("Validation Failed: Transfer already approved");
        }
        if (transferState != "waiting")
        {
            throw new InvalidOperationException("Validation Failed: Transfer doesn't require approval");
        }
    }

    private void UpsertStep(string step) {
        if (ADVANCED_VISIBILITY == Workflow.Info.WorkflowType) {
            Workflow.Logger.LogInformation("Advanced visibility .. {}", step);
            Workflow.UpsertTypedSearchAttributes(stepAttributKey.ValueSet(step));
        }
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
