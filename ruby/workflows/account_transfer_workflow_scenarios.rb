# frozen_string_literal: true

require_relative 'account_transfer_workflow'
require 'temporalio/error'
require 'timeout'

module Workflows
  class AccountTransferWorkflowScenarios < AccountTransferWorkflow
    # This workflow is designed to demonstrate various scenarios for the Account Transfer Workflow.

    # `workflow_dynamic` makes this workflow to catch all the workflow types that is not otherwise
    # registered by the worker, i.e. AccountTransferWorkflowRecoverableFailure,
    # AccountTransferWorkflowHumanInLoop and AccountTransferWorkflowAdvancedVisibility.
    workflow_dynamic

    BUG = 'AccountTransferWorkflowRecoverableFailure'
    NEEDS_APPROVAL = 'AccountTransferWorkflowHumanInLoop'
    ADVANCED_VISIBILITY = 'AccountTransferWorkflowAdvancedVisibility'

    APPROVAL_TIME = 30

    attr_reader :approved

    def initialize
      super
      @approved = false
    end

    def execute(input)
      workflow_type = Temporalio::Workflow.info.workflow_type
      logger.info("Dynamic Account Transfer Workflow started: #{workflow_type}, input: #{input.to_h}")

      idempotency_key = Temporalio::Workflow.random.uuid

      upsert_step('Validate')
      validate_transfer(input)
      update_progress(25, 1)

      handle_approval_if_needed(workflow_type)

      upsert_step('Withdraw')
      withdraw_funds(idempotency_key, input.fetch('amount'), workflow_type)
      update_progress(50, 3)

      handle_bug_simulation(workflow_type)

      upsert_step('Deposit')
      begin
        @deposit_response = deposit_funds(idempotency_key, input.fetch('amount'), workflow_type)
        update_progress(75, 1)
      rescue StandardError => e
        logger.info('Deposit failed unrecoverable error, reverting withdraw')
        undo_withdraw(input.fetch('amount'))
        raise StandardError, "Deposit failed: #{e.message}"
      end

      upsert_step('SendNotification')
      send_notification(input)
      update_progress(100, 1, 'finished')

      Models::TransferOutput.new(deposit_response: @deposit_response).to_h
    end

    workflow_signal(name: 'approveTransfer')
    def approve_transfer_signal
      logger.info('Approve Signal Received')
      if @transfer_state == 'waiting'
        @approved = true
      else
        logger.info('Approval not applied. Transfer is not waiting for approval')
      end
    end

    workflow_query(name: 'transferStatus')
    def query_transfer_status
      Models::TransferStatus.new(
        progress_percentage: progress,
        transfer_state: transfer_state,
        workflow_status: '',
        charge_result: deposit_response,
        approval_time: APPROVAL_TIME
      ).to_h
    end

    private

    def handle_approval_if_needed(workflow_type)
      return unless workflow_type == NEEDS_APPROVAL

      logger.info("Waiting on 'approveTransfer' Signal for workflow ID: #{Temporalio::Workflow.info.workflow_id}")
      update_progress(30, 0, 'waiting')

      begin
        Temporalio::Workflow.timeout(APPROVAL_TIME) { Temporalio::Workflow.wait_condition { approved } }
      rescue Timeout::Error
        logger.error("Approval not received within #{APPROVAL_TIME} seconds")
        raise Temporalio::Error::ApplicationError.new("Approval not received within #{APPROVAL_TIME} seconds", non_retryable: true)
      end
    end

    def handle_bug_simulation(workflow_type)
      return unless workflow_type == BUG

      raise 'Simulated bug - fix me!'
    end

    def undo_withdraw(amount)
      Temporalio::Workflow.execute_activity(
        'Activities::UndoWithdrawActivity',
        amount,
        start_to_close_timeout: 5,
        retry_policy: Activities::BaseActivity::RETRY_POLICY
      )
    end

    def upsert_step(step)
      return unless Temporalio::Workflow.info.workflow_type == ADVANCED_VISIBILITY

      logger.info("Advanced visibility... On step: #{step}")
      Temporalio::Workflow.upsert_search_attributes('Step' => step)
    end
  end
end
