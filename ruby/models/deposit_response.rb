# frozen_string_literal: true

require 'active_support/inflector'

module Models
  DepositResponse = Data.define(:charge_id) do
    def to_h
      super.transform_keys { |key| key.to_s.camelize(:lower) }
    end
  end
end
