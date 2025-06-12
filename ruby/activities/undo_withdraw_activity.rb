# frozen_string_literal: true

require_relative 'base_activity'

module Activities
  class UndoWithdrawActivity < BaseActivity
    def execute(amount)
      logger.info("Undo withdraw activity started. Amount: #{amount}")
      simulate_external_operation(1000)
      true
    end
  end
end
