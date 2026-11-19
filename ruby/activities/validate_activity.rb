# frozen_string_literal: true

require_relative 'base_activity'
require_relative '../models/transfer_input'

module Activities
  class ValidateActivity < BaseActivity
    def execute(input)
      input = Models::TransferInput.from_h(input)
      logger.info("Validate activity started. Input: #{input.to_h}")
      simulate_external_operation(1000)
      'SUCCESS'
    end
  end
end
