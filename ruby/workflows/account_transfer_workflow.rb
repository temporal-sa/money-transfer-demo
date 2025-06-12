# frozen_string_literal: true

require 'temporalio/workflow'
require_relative '../models/transfer_input'
require_relative '../models/transfer_output'
require_relative '../models/transfer_status'
require_relative '../models/deposit_response'

module Workflows
  class AccountTransferWorkflow < Temporalio::Workflow::Definition
    attr_reader :progress, :transfer_state, :deposit_response

    def initialize
      @progress = 0
      @transfer_state = ''
      @deposit_response = Models::DepositResponse.new(charge_id: '')
    end

    def execute(input)
      workflow_type = Temporalio::Workflow.info.workflow_type
      logger.info("Simple workflow started: #{workflow_type}, input: #{input.to_h}")

      idempotency_key = Temporalio::Workflow.random.uuid

      validate_transfer(input)
      update_progress(25, 1)

      withdraw_funds(idempotency_key, input.fetch('amount'), workflow_type)
      update_progress(50, 3)

      @deposit_response = deposit_funds(idempotency_key, input.fetch('amount'), workflow_type)
      update_progress(75, 1)

      send_notification(input)
      update_progress(100, 1, 'finished')

      Models::TransferOutput.new(deposit_response: @deposit_response).to_h
    end

    workflow_query(name: 'transferStatus')
    def query_transfer_status
      logger.info('Workflow has been queried')
      Models::TransferStatus.new(
        progress_percentage: progress,
        transfer_state: transfer_state,
        workflow_status: '',
        charge_result: deposit_response.to_h,
        approval_time: 0
      ).to_h
    end

    private

    def validate_transfer(input)
      Temporalio::Workflow.execute_activity(
        Activities::ValidateActivity,
        input,
        start_to_close_timeout: 5,
        retry_policy: Activities::BaseActivity::RETRY_POLICY
      )
    end

    def withdraw_funds(idempotency_key, amount, workflow_type)
      Temporalio::Workflow.execute_activity(
        Activities::WithdrawActivity,
        idempotency_key, amount,
        start_to_close_timeout: 5,
        retry_policy: Activities::BaseActivity::RETRY_POLICY
      )
    end

    def deposit_funds(idempotency_key, amount, workflow_type)
      Temporalio::Workflow.execute_activity(
        Activities::DepositActivity,
        idempotency_key, amount,
        start_to_close_timeout: 5,
        retry_policy: Activities::BaseActivity::RETRY_POLICY
      )
    end

    def send_notification(input)
      Temporalio::Workflow.execute_activity(
        Activities::SendNotificationActivity,
        input,
        start_to_close_timeout: 5,
        retry_policy: Activities::BaseActivity::RETRY_POLICY
      )
    end

    def update_progress(progress, sleep_duration, state = 'running')
      sleep(sleep_duration) if sleep_duration > 0
      @transfer_state = state
      @progress = progress
    end

    def logger
      @logger ||= Temporalio::Workflow.logger
    end
  end
end
