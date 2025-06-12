# frozen_string_literal: true

require 'active_support/inflector'
require_relative 'deposit_response'

module Models
  TransferOutput = Data.define(:deposit_response) do
    def to_h
      super.transform_keys { |key| key.to_s.camelize(:lower) }
    end
  end
end
