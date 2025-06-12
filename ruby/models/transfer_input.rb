# frozen_string_literal: true

require 'active_support/inflector'

module Models
  TransferInput = Data.define(:amount, :from_account, :to_account) do
    def to_h
      super.transform_keys { |key| key.to_s.camelize(:lower) }
    end
  end
end
