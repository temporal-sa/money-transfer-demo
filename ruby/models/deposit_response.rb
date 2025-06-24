# frozen_string_literal: true

require 'json/add/struct'
require_relative 'serialization'

module Models
  DepositResponse = Struct.new(:charge_id) do
    include Serialization
  end
end
