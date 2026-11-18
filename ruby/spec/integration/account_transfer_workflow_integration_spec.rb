# frozen_string_literal: true

require 'spec_helper'
require 'securerandom'
require_relative '../../workflows/account_transfer_workflow'
require_relative '../../activities/validate_activity'
require_relative '../../activities/withdraw_activity'
require_relative '../../activities/deposit_activity'
require_relative '../../activities/send_notification_activity'
require_relative '../../models/transfer_input'

RSpec.describe 'AccountTransferWorkflow Integration', :integration do
  let(:transfer_input) do
    {amount: 100, fromAccount: 'account1', toAccount: 'account2'}
  end

  it 'executes the workflow end-to-end' do
    Temporalio::Testing::WorkflowEnvironment.start_local do |env|
      task_queue = "tq-#{SecureRandom.uuid}"
      workflow_id = "wf-#{SecureRandom.uuid}"

      worker = Temporalio::Worker.new(
        client: env.client,
        task_queue: task_queue,
        workflows: [Workflows::AccountTransferWorkflow],
        activities: [
          Activities::ValidateActivity,
          Activities::WithdrawActivity,
          Activities::DepositActivity,
          Activities::SendNotificationActivity
        ]
      )

      worker.run do
        # Start workflow
        handle = env.client.start_workflow(
          Workflows::AccountTransferWorkflow,
          transfer_input,
          id: workflow_id,
          task_queue: task_queue
        )

        # Wait for result
        result = handle.result

        # Verify result
        expect(result).to be_a(Hash)
        expect(result['depositResponse']).to be_a(Hash)
        expect(result['depositResponse']['chargeId']).not_to be_empty

        # Query workflow status
        status = handle.query('transferStatus')
        expect(status['progressPercentage']).to eq(100)
        expect(status['transferState']).to eq('finished')
      end
    end
  end

  it 'handles workflow cancellation' do
    Temporalio::Testing::WorkflowEnvironment.start_local do |env|
      task_queue = "tq-#{SecureRandom.uuid}"
      workflow_id = "wf-#{SecureRandom.uuid}"

      # Create a mock activity that will take longer to complete
      slow_activity = Class.new(Activities::DepositActivity) do
        def deposit(idempotency_key, amount)
          sleep 5
          super
        end
      end

      worker = Temporalio::Worker.new(
        client: env.client,
        task_queue: task_queue,
        workflows: [Workflows::AccountTransferWorkflow],
        activities: [
          Activities::ValidateActivity,
          Activities::WithdrawActivity,
          slow_activity,
          Activities::SendNotificationActivity
        ]
      )

      worker.run do
        # Start workflow
        handle = env.client.start_workflow(
          Workflows::AccountTransferWorkflow,
          transfer_input,
          id: workflow_id,
          task_queue: task_queue
        )

        # Wait for activity to be scheduled
        sleep 0.5 until handle.describe.raw_description.pending_activities.any?

        # Cancel workflow
        handle.cancel

        # Check that it was cancelled
        expect { handle.result }.to raise_error(Temporalio::Error::WorkflowFailedError, /Workflow execution canceled/)
      end
    end
  end
end
