# frozen_string_literal: true

require 'active_support/inflector'
require_relative 'deposit_response'

module Models
  TransferStatus = Data.define(
    :progress_percentage,
    :transfer_state,
    :workflow_status,
    :charge_result,
    :approval_time
  ) do
    def to_h
      super.transform_keys { |key| key.to_s.camelize(:lower) }
    end
  end
end
