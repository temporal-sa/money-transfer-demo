# frozen_string_literal: true

require 'spec_helper'
require 'securerandom'
require_relative '../../workflows/account_transfer_workflow_scenarios'
require_relative '../../activities/validate_activity'
require_relative '../../activities/withdraw_activity'
require_relative '../../activities/deposit_activity'
require_relative '../../activities/send_notification_activity'
require_relative '../../activities/undo_withdraw_activity'
require_relative '../../models/transfer_input'

RSpec.describe 'AccountTransferWorkflowScenarios Integration', :integration do
  let(:transfer_input) do
    Models::TransferInput.new(
      amount: 100,
      from_account: 'account1',
      to_account: 'account2'
    )
  end

  def worker(env, task_queue)
    Temporalio::Worker.new(
      client: env.client,
      task_queue: task_queue,
      workflows: [Workflows::AccountTransferWorkflowScenarios],
      activities: [
        Activities::ValidateActivity,
        Activities::WithdrawActivity,
        Activities::DepositActivity,
        Activities::SendNotificationActivity,
        Activities::UndoWithdrawActivity
      ]
    )
  end

  let(:task_queue) { "tq-#{SecureRandom.uuid}" }

  let(:workflow_id) { "wf-#{SecureRandom.uuid}" }

  it 'handles human-in-loop workflow with approval' do
    Temporalio::Testing::WorkflowEnvironment.start_local do |env|
      worker(env, task_queue).run do
        handle = env.client.start_workflow(
          Workflows::AccountTransferWorkflowScenarios::NEEDS_APPROVAL,
          transfer_input.to_h,
          id: workflow_id,
          task_queue: task_queue
        )
        
        # Wait for workflow to reach waiting state
        sleep 0.5 until handle.query('transferStatus')['transferState'] == 'waiting'
        
        # Send approval signal
        handle.signal('approveTransfer')
        
        # Wait for result
        result = handle.result
        
        expect(result['depositResponse']).to include('chargeId' => 'example-transfer-id')
        
        status = handle.query('transferStatus')
        expect(status['progressPercentage']).to eq(100)
        expect(status['transferState']).to eq('finished')
      end
    end
  end
  
  it 'fails when human-in-loop workflow times out' do
    Temporalio::Testing::WorkflowEnvironment.start_local do |env|
      # Override approval time to make test faster
      stub_const("Workflows::AccountTransferWorkflowScenarios::APPROVAL_TIME", 1)
      
      worker(env, task_queue).run do
        handle = env.client.start_workflow(
          Workflows::AccountTransferWorkflowScenarios::NEEDS_APPROVAL,
          transfer_input.to_h,
          id: workflow_id,
          task_queue: task_queue
        )
        
        # Wait for workflow to reach waiting state
        sleep 0.5 until handle.query('transferStatus')['transferState'] == 'waiting'
        
        # Don't send approval signal and let it time out
        begin
          handle.result
        rescue Temporalio::Error::WorkflowFailedError => e
          expect(e.cause.message).to include('Approval not received within')
        end
      end
    end
  end
end
