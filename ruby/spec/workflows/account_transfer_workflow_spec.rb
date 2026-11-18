# frozen_string_literal: true

require 'spec_helper'
require_relative '../../workflows/account_transfer_workflow'
require_relative '../../models/transfer_input'
require_relative '../../models/deposit_response'
require_relative '../../models/transfer_status'
require_relative '../../activities/validate_activity'
require_relative '../../activities/withdraw_activity'
require_relative '../../activities/deposit_activity'
require_relative '../../activities/send_notification_activity'
require_relative '../../activities/undo_withdraw_activity'

RSpec.describe Workflows::AccountTransferWorkflow do
  let(:workflow) { described_class.new }
  let(:hash_input) do
    {amount: 100, fromAccount: 'account1', toAccount: 'account2'}
  end
  let(:transfer_input) do
    Models::TransferInput.from_h(hash_input)
  end  
  let(:deposit_response) { Models::DepositResponse.new(charge_id: 'test-charge-id') }

  before do
    allow(Temporalio::Workflow).to receive(:info).and_return(
      double(workflow_type: 'AccountTransferWorkflow')
    )
    allow(Temporalio::Workflow).to receive(:logger).and_return(
      double(info: nil)
    )
    allow(Temporalio::Workflow).to receive(:random).and_return(
      double(uuid: 'test-uuid')
    )
  end

  describe '#query_transfer_status' do
    it 'returns current transfer status' do
      workflow.instance_variable_set(:@progress, 50)
      workflow.instance_variable_set(:@transfer_state, 'running')
      workflow.instance_variable_set(:@deposit_response, deposit_response)

      status = workflow.query_transfer_status

      expect(status).to include(
        'progressPercentage' => 50,
        'transferState' => 'running',
        'workflowStatus' => '',
        'chargeResult' => { 'chargeId' => 'test-charge-id' },
        'approvalTime' => 0
      )
    end
  end

  describe '#execute' do
    before do
      allow(Temporalio::Workflow).to receive(:execute_activity).and_return('SUCCESS')
      allow(workflow).to receive(:sleep)
    end

    it 'processes the transfer through all steps' do
      allow(Temporalio::Workflow).to receive(:execute_activity)
        .with(Activities::DepositActivity, anything, anything, any_args)
        .and_return(deposit_response)

      result = workflow.execute(hash_input)

      # Verify all activities were called
      expect(Temporalio::Workflow).to have_received(:execute_activity)
        .with(Activities::ValidateActivity, transfer_input, any_args)
      expect(Temporalio::Workflow).to have_received(:execute_activity)
        .with(Activities::WithdrawActivity, 'test-uuid', 100, any_args)
      expect(Temporalio::Workflow).to have_received(:execute_activity)
        .with(Activities::DepositActivity, 'test-uuid', 100, any_args)
      expect(Temporalio::Workflow).to have_received(:execute_activity)
        .with(Activities::SendNotificationActivity, transfer_input, any_args)

      # Verify workflow state
      expect(workflow).to have_attributes(
        progress: 100,
        transfer_state: 'finished',
        deposit_response: deposit_response
      )
      # Verify result
      expect(result['depositResponse']).to eq({ 'chargeId' => 'test-charge-id' })
    end

    it 'updates progress correctly during execution' do
      allow(Temporalio::Workflow).to receive(:execute_activity)
        .with(Activities::DepositActivity, anything, anything, any_args)
        .and_return(deposit_response)

      expect(workflow).to receive(:update_progress).with(25, 1).ordered
      expect(workflow).to receive(:update_progress).with(50, 3).ordered
      expect(workflow).to receive(:update_progress).with(75, 1).ordered
      expect(workflow).to receive(:update_progress).with(100, 0, 'finished').ordered

      workflow.execute(hash_input)
    end
  end
end
