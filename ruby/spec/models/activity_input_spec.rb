# frozen_string_literal: true

require 'spec_helper'
require 'temporalio/converters'
require_relative '../../models/activity_input'
require_relative '../../models/deposit_response'
require_relative '../../models/transfer_input'

RSpec.describe 'Activity payloads' do
  let(:converter) { Temporalio::Converters::PayloadConverter.default }

  def round_trip(value)
    payload = converter.to_payload(value)
    [JSON.parse(payload.data), converter.from_payload(payload)]
  end

  it 'sends ActivityInput as a camelCase object and rebuilds it with from_h' do
    input = Models::ActivityInput.new(idempotency_key: 'key123', amount: 100)

    json, received = round_trip(input.deep_camelize_keys)

    expect(json).to eq('idempotencyKey' => 'key123', 'amount' => 100)
    expect(Models::ActivityInput.from_h(received)).to eq(input)
  end

  it 'sends TransferInput as a camelCase object and rebuilds it with from_h' do
    input = Models::TransferInput.new(amount: 100, from_account: 'Checking', to_account: 'Savings')

    json, received = round_trip(input.deep_camelize_keys)

    expect(json).to eq('amount' => 100, 'fromAccount' => 'Checking', 'toAccount' => 'Savings')
    expect(Models::TransferInput.from_h(received)).to eq(input)
  end

  it 'returns DepositResponse as a camelCase object and rebuilds it with from_h' do
    response = Models::DepositResponse.new(charge_id: 'example-transfer-id')

    json, received = round_trip(response.deep_camelize_keys)

    expect(json).to eq('chargeId' => 'example-transfer-id')
    expect(Models::DepositResponse.from_h(received)).to eq(response)
  end
end
