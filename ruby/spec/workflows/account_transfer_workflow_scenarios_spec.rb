# frozen_string_literal: true

require 'spec_helper'
require_relative '../../workflows/account_transfer_workflow_scenarios'
require_relative '../../models/transfer_input'
require_relative '../../models/deposit_response'
require_relative '../../models/transfer_status'

RSpec.describe Workflows::AccountTransferWorkflowScenarios do
  let(:workflow) { described_class.new }
  let(:transfer_input) do
    {amount: 100, fromAccount: 'account1', toAccount: 'account2'}
  end
  let(:deposit_response) { Models::DepositResponse.new(charge_id: 'test-charge-id') }
  let(:workflow_id) { 'test-workflow-id' }

  before do
    allow(Temporalio::Workflow).to receive(:info).and_return(
      double(workflow_type: 'AccountTransferWorkflow', workflow_id: workflow_id)
    )
    allow(Temporalio::Workflow).to receive(:logger).and_return(
      double(info: nil, error: nil)
    )
    allow(Temporalio::Workflow).to receive(:random).and_return(
      double(uuid: 'test-uuid')
    )
    allow(Temporalio::Workflow).to receive(:execute_activity).and_return('SUCCESS')
    allow(workflow).to receive(:sleep)
  end

  describe '#execute' do
    context 'with standard workflow' do
      it 'processes the transfer successfully' do
        allow(Temporalio::Workflow).to receive(:execute_activity)
          .with(Activities::DepositActivity, anything, anything, any_args)
          .and_return(deposit_response)

        result = workflow.execute(transfer_input)

        expect(workflow.progress).to eq(100)
        expect(workflow.transfer_state).to eq('finished')
        expect(result).to be_a(Hash)
        expect(result['depositResponse']).to eq({ 'chargeId' => 'test-charge-id' })
      end
    end

    context 'with human-in-loop workflow' do
      before do
        allow(Temporalio::Workflow).to receive(:info).and_return(
          double(workflow_type: described_class::NEEDS_APPROVAL, workflow_id: workflow_id)
        )
      end

      it 'waits for approval and completes when approved' do
        allow(Temporalio::Workflow).to receive(:timeout).and_yield
        allow(Temporalio::Workflow).to receive(:wait_condition).and_yield
        allow(Temporalio::Workflow).to receive(:execute_activity)
          .with(Activities::DepositActivity, anything, anything, any_args)
          .and_return(deposit_response)

        workflow.execute(transfer_input)

        expect(workflow.progress).to eq(100)
        expect(workflow.transfer_state).to eq('finished')
      end

      it 'raises error when approval times out' do
        allow(Temporalio::Workflow).to receive(:timeout)
          .and_raise(Timeout::Error)

        begin
          workflow.execute(transfer_input)
        rescue Temporalio::Error::ApplicationError => e
          expect(e.message).to include('Approval not received within')
        end
      end
    end

    context 'with recoverable failure workflow' do
      before do
        allow(Temporalio::Workflow).to receive(:info).and_return(
          double(workflow_type: described_class::BUG, workflow_id: workflow_id)
        )
      end

      it 'raises simulated bug error' do
        expect do
          workflow.execute(transfer_input)
        end.to raise_error('Simulated bug - fix me!')
      end
    end

    context 'with advanced visibility workflow' do
      before do
        allow(Temporalio::Workflow).to receive(:info).and_return(
          double(workflow_type: described_class::ADVANCED_VISIBILITY, workflow_id: workflow_id)
        )
        allow(Temporalio::Workflow).to receive(:upsert_search_attributes)
      end

      it 'upserts search attributes for each step' do
        allow(Temporalio::Workflow).to receive(:execute_activity)
          .with(Activities::DepositActivity, anything, anything, any_args)
          .and_return(deposit_response)

        workflow.execute(transfer_input)

        RSpec::Matchers.define :_attr_value do |expected_value|
          match do |actual|
            actual.is_a?(Temporalio::SearchAttributes::Update) && actual.value == expected_value
          end
        end

        expect(Temporalio::Workflow).to have_received(:upsert_search_attributes)
          .with(_attr_value('Validate'))
        expect(Temporalio::Workflow).to have_received(:upsert_search_attributes)
          .with(_attr_value('Withdraw'))
        expect(Temporalio::Workflow).to have_received(:upsert_search_attributes)
          .with(_attr_value('Deposit'))
        expect(Temporalio::Workflow).to have_received(:upsert_search_attributes)
          .with(_attr_value('SendNotification'))
      end
    end

    context 'when deposit fails' do
      it 'reverts withdraw and raises error' do
        allow(Temporalio::Workflow).to receive(:execute_activity)
          .with(Activities::DepositActivity, anything, anything, any_args)
          .and_raise(StandardError.new('Deposit failed'))

        expect(workflow).to receive(:undo_withdraw).with(100)

        expect do
          workflow.execute(transfer_input)
        end.to raise_error(StandardError, /Deposit failed/)
      end
    end
  end

  describe '#approve_transfer_signal' do
    context 'when transfer is waiting for approval' do
      before do
        workflow.instance_variable_set(:@transfer_state, 'waiting')
      end

      it 'approves the transfer' do
        workflow.approve_transfer_signal
        expect(workflow.approved).to be true
      end
    end

    context 'when transfer is not waiting for approval' do
      before do
        workflow.instance_variable_set(:@transfer_state, 'running')
      end

      it 'does not approve the transfer' do
        workflow.approve_transfer_signal
        expect(workflow.approved).to be false
      end
    end
  end

  describe '#query_transfer_status' do
    before do
      workflow.instance_variable_set(:@progress, 50)
      workflow.instance_variable_set(:@transfer_state, 'running')
      workflow.instance_variable_set(:@deposit_response, deposit_response)
    end

    it 'returns current transfer status with approval time' do
      status = workflow.query_transfer_status

      expect(status['progressPercentage']).to eq(50)
      expect(status['transferState']).to eq('running')
      expect(status['approvalTime']).to eq(described_class::APPROVAL_TIME)
      expect(status['chargeResult']).to eq({ 'chargeId' => 'test-charge-id' })
    end
  end
end
