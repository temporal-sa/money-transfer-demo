require 'json'
require 'active_support/inflector'
require 'active_support/core_ext/hash/keys'

module Models
  # Converts models to and from the camelCase hashes that go over the wire, so Ruby payloads
  # look the same as the other language workers' payloads (e.g. {"idempotencyKey": ..., "amount": ...}).
  #
  # Ruby has no type hints, so the default Temporal converter hands activities and workflows a plain
  # Hash. Callers send `model.deep_camelize_keys` and receivers rebuild the model with `Model.from_h`.
  module Serialization
    def self.included(base)
      base.extend(ClassMethods)
      base.class_eval do
        def deep_camelize_keys
          deep_to_h.deep_transform_keys { |key| key.to_s.camelize(:lower) }
        end

        def deep_to_h
          hash = {}
          members.each do |member|
            value = send(member)
            hash[member] = if value.respond_to?(:deep_to_h)
                             value.deep_to_h
                           elsif value.respond_to?(:to_h)
                             value.to_h
                           else
                             value
                           end
          end
          hash
        end
      end
    end

    module ClassMethods
      # Builds the model from a hash with camelCase or snake_case keys. Unknown keys are ignored.
      def from_h(hash)
        symbolized = hash.deep_transform_keys { |key| key.to_s.underscore.to_sym }
        new(**symbolized.slice(*members))
      end
    end
  end
end
