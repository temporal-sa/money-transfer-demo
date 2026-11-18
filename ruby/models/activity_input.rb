# frozen_string_literal: true

require_relative 'serialization'

module Models
  # Input to the withdraw and deposit activities. The workflow type is read from the activity context.
  ActivityInput = Struct.new(:idempotency_key, :amount) do
    include Serialization
  end
end
