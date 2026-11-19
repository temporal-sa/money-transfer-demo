# frozen_string_literal: true

require_relative 'serialization'

module Models
  ActivityInput = Struct.new(:idempotency_key, :amount) do
    include Serialization
  end
end
