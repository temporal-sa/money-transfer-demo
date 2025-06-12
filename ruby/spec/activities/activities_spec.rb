# frozen_string_literal: true

require 'spec_helper'
require_relative '../../activities/validate_activity'
require_relative '../../activities/withdraw_activity'
require_relative '../../activities/deposit_activity'
require_relative '../../activities/send_notification_activity'
require_relative '../../activities/undo_withdraw_activity'
require_relative '../../models/transfer_input'

RSpec.describe 'Activities' do
  before do
    allow(subject).to receive(:sleep)
  end

  let(:transfer_input) do
    Models::TransferInput.new(
      amount: 2000,
      from_account: 'account1',
      to_account: 'account2'
    )
  end

  let(:info) do
    Temporalio::Testing::ActivityEnvironment.default_info
  end

  let(:env) do
    Temporalio::Testing::ActivityEnvironment.new(info: info)
  end

  describe Activities::ValidateActivity do
    it 'successfully validates transfer input' do
      result = env.run(subject, transfer_input)
      expect(result).to eq('SUCCESS')
    end
  end

  describe Activities::WithdrawActivity do
    it 'successfully withdraws funds' do
      result = env.run(subject, 'key123', 123)
      expect(subject).to have_received(:sleep).with(1.0)
      expect(result).to eq('SUCCESS')
    end

    context 'when API is unavailable' do
      let(:info) do
        Temporalio::Testing::ActivityEnvironment.default_info.with(
          workflow_type: 'AccountTransferWorkflowAPIDowntime'
        )
      end

      it 'raises error for API downtime scenario' do
        expect do
          env.run(subject, 'key123', 123)
        end.to raise_error(StandardError, 'Withdraw activity failed, API unavailable')
      end
    end

    context 'when attempts is over 5' do
      let(:info) do
        Temporalio::Testing::ActivityEnvironment.default_info.with(
          workflow_type: 'AccountTransferWorkflowAPIDowntime',
          attempt: 5
        )
      end
      
      it 'does not raise error for API downtime scenario' do
        expect do
          env.run(subject, 'key123', 123)
        end.not_to raise_error
      end
    end   
  end

  describe Activities::DepositActivity do
    it 'successfully deposits funds' do
      result = env.run(subject, 'key123', 123)
      expect(subject).to have_received(:sleep).with(1.0)
      expect(result).to be_a(Hash)
      expect(result).to include('chargeId' => 'example-transfer-id')
    end

    context 'when scheduled by AccountTransferWorkflowInvalidAccount workflow' do
      let(:info) do
        Temporalio::Testing::ActivityEnvironment.default_info.with(
          workflow_type: 'AccountTransferWorkflowInvalidAccount'
        )
      end

      it 'raises error for invalid account scenario' do
        expect do
          env.run(subject, 'key123', 123)
        end.to raise_error(ArgumentError, 'Deposit activity failed, account is invalid')
      end
    end

    context 'when not scheduled by AccountTransferWorkflowInvalidAccount workflow' do
      let(:info) do
        Temporalio::Testing::ActivityEnvironment.default_info.with(
          workflow_type: 'SomeOtherWorkflowType'
        )
      end

      it 'does not raise error for invalid account scenario' do
        expect do
          env.run(subject, 'key123', 123)
        end.not_to raise_error
      end
    end    
  end

  describe Activities::SendNotificationActivity do
    it 'successfully sends notification' do
      result = env.run(subject, transfer_input)
      expect(result).to eq('SUCCESS')
    end
  end

  describe Activities::UndoWithdrawActivity do
    it 'successfully undoes withdrawal' do
      result = env.run(subject, 123)
      expect(result).to be(true)
      expect(subject).to have_received(:sleep).with(1.0)
    end
  end
end
