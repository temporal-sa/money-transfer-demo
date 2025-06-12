# frozen_string_literal: true

require_relative 'base_activity'

module Activities
  class WithdrawActivity < BaseActivity
    API_DOWNTIME = 'AccountTransferWorkflowAPIDowntime'

    def execute(idempotency_key, amount)
      attempt = Temporalio::Activity::Context.current.info.attempt
      workflow_type = Temporalio::Activity::Context.current.info.workflow_type
      logger.info("Withdraw activity started. Amount: #{amount}, workflow type: #{workflow_type}, attempt: #{attempt}")

      error = simulate_external_operation_with_error(1000, workflow_type, attempt)
      logger.info("Withdraw call complete, type: #{workflow_type}, error: #{error}")

      if error == API_DOWNTIME
        logger.info("Withdraw API unavailable, attempt: #{attempt}")
        raise StandardError, 'Withdraw activity failed, API unavailable'
      end

      'SUCCESS'
    end
  end
end
