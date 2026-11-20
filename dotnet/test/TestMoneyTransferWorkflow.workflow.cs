using Temporalio.Client;
using Temporalio.Testing;
using Temporalio.Worker;
using Temporalio.Exceptions;
using Xunit;

using MoneyTransfer;

namespace MoneyTransferTests;

public class MoneyTransferTests
{

    [Fact]
    public async Task RunAsync_MoneyTransfer_HappyPath()
    {
         await using var env = await WorkflowEnvironment.StartTimeSkippingAsync();
         var clientOptions = (TemporalClientOptions)env.Client.Options.Clone();
         var client = new TemporalClient(env.Client.Connection, clientOptions);
         var taskQueue = Guid.NewGuid().ToString();
         var workerOptions = new TemporalWorkerOptions(taskQueue).
            AddAllActivities(new AccountTransferActivities()).
            AddWorkflow<AccountTransferWorkflow>().
            AddWorkflow<AccountTransferWorkflowScenarios>();

        using var worker = new TemporalWorker(client, workerOptions);
        await worker.ExecuteAsync(async () =>
        {
            var input = new TransferInput(1000, "account1", "account2");
            var handle = await client.StartWorkflowAsync(
                (AccountTransferWorkflow wf) => wf.Transfer(input),
                new(
                    id: "HappyPathID",
                    taskQueue: taskQueue));

            // Wait for the workflow to complete
            var result = await handle.GetResultAsync<TransferOutput>();
            var expected = new TransferOutput(new DepositResponse("example-transfer-id"));
            Assert.Equivalent(expected, result);
        });
    }

    [Fact]
    public async Task RunAsync_MoneyTransfer_HumanInLoop_Approved()
    {
         await using var env = await WorkflowEnvironment.StartLocalAsync();
         var clientOptions = (TemporalClientOptions)env.Client.Options.Clone();
         var client = new TemporalClient(env.Client.Connection, clientOptions);
         var taskQueue = Guid.NewGuid().ToString();
         var workerOptions = new TemporalWorkerOptions(taskQueue).
            AddAllActivities(new AccountTransferActivities()).
            AddWorkflow<AccountTransferWorkflow>().
            AddWorkflow<AccountTransferWorkflowScenarios>();

        using var worker = new TemporalWorker(client, workerOptions);
        await worker.ExecuteAsync(async () =>
        {
            var input = new TransferInput(1000, "account1", "account2");

            var handle = await client.StartWorkflowAsync(
                "AccountTransferWorkflowHumanInLoop",
                new object?[] { input },
                new(
                    id: "HumanInLoopID",
                    taskQueue: taskQueue));

            // Skip time so we're waiting for a signal
            Thread.Sleep(TimeSpan.FromSeconds(ServerInfo.WorkflowSleepDuration+1));

            // signal the workflow
            IReadOnlyCollection<string> emptyReadOnlyCollection = Array.Empty<string>();
            await handle.SignalAsync("approveTransfer", emptyReadOnlyCollection);

            // Wait for the workflow to complete
            var result = await handle.GetResultAsync<TransferOutput>();
            var expected = new TransferOutput(new DepositResponse("example-transfer-id"));
            Assert.Equivalent(expected, result);
        });
    }

    [Fact]
    public async Task RunAsync_MoneyTransfer_HumanInLoop_NotApproved()
    {
         await using var env = await WorkflowEnvironment.StartTimeSkippingAsync();
         var clientOptions = (TemporalClientOptions)env.Client.Options.Clone();
         var client = new TemporalClient(env.Client.Connection, clientOptions);
         var taskQueue = Guid.NewGuid().ToString();
         var workerOptions = new TemporalWorkerOptions(taskQueue).
            AddAllActivities(new AccountTransferActivities()).
            AddWorkflow<AccountTransferWorkflow>().
            AddWorkflow<AccountTransferWorkflowScenarios>();

        using var worker = new TemporalWorker(client, workerOptions);
        await worker.ExecuteAsync(async () =>
        {
            var input = new TransferInput(1000, "account1", "account2");

            var handle = await client.StartWorkflowAsync(
                "AccountTransferWorkflowHumanInLoop",
                new object?[] { input },
                new(
                    id: "HumanInLoopID",
                    taskQueue: taskQueue));

            // Wait for the workflow to complete
            // will fail because it wasn't approved
            await Assert.ThrowsAsync<WorkflowFailedException> (async () => await handle.GetResultAsync());
        });
    }
}
