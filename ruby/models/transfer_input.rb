# frozen_string_literal: true

require_relative 'serialization'

module Models
  TransferInput = Struct.new(:amount, :from_account, :to_account) do
    include Serialization
  end
end
