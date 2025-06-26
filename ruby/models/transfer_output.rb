# frozen_string_literal: true

require 'json/add/struct'
require_relative 'serialization'

module Models
  TransferOutput = Struct.new(:deposit_response) do
    include Serialization
  end
end
