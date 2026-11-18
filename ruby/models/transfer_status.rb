# frozen_string_literal: true

require_relative 'serialization'

module Models
  TransferStatus = Struct.new(
    :progress_percentage,
    :transfer_state,
    :workflow_status,
    :charge_result,
    :approval_time
  ) do
    include Serialization
  end
end
