# frozen_string_literal: true

require 'active_support/inflector'
require 'active_support/core_ext/hash/keys'
require_relative 'serialization'

module Models
  ActivityInput = Struct.new(:idempotency_key, :amount) do
    include Serialization

    def self.from_h(hash)
      symbolized = hash.deep_transform_keys { |key| key.to_s.underscore.to_sym }
      new(**symbolized.slice(:idempotency_key, :amount))
    end
  end
end
