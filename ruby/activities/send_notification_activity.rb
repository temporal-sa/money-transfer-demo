# frozen_string_literal: true

require_relative 'base_activity'

module Activities
  class SendNotificationActivity < BaseActivity
    def execute(input)
      logger.info("Send notification activity started. Input: #{input.to_h}")
      simulate_external_operation(1000)
      'SUCCESS'
    end
  end
end
