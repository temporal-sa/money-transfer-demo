require 'spec_helper'
require_relative '../../security/encryption_codec'
require 'temporalio/api'

RSpec.describe Security::EncryptionCodec do
  let(:key_id) { 'test-key-id' }
  let(:key) { 'sa-rocks!sa-rocks!sa-rocks!yeah!' }
  let(:codec) { described_class.new(key_id, key) }
  let(:default_codec) { described_class.new }

  describe '#encode' do
    it 'encrypts payloads with the provided key' do
      payload = Temporalio::Api::Common::V1::Payload.new(
        metadata: { 'content-type' => 'application/json' },
        data: '{"test": "data"}'
      )

      result = codec.encode([payload, payload])

      expect(result.size).to eq(2)
      expect(result[0].metadata['encoding']).to eq('binary/encrypted')
      expect(result[0].metadata['encryption-key-id']).to eq(key_id)
      expect(result[0].data).not_to eq(payload.data)
    end
  end

  describe '#decode' do
    it 'decrypts payloads that were encrypted with the same key' do
      original_payload = Temporalio::Api::Common::V1::Payload.new(
        metadata: { 'content-type' => 'application/json' },
        data: '{"test": "data"}'
      )

      encoded = codec.encode([original_payload])
      decoded = codec.decode(encoded)

      expect(decoded.size).to eq(1)
      expect(decoded[0].metadata).to eq(original_payload.metadata)
      expect(decoded[0].data).to eq(original_payload.data)
    end

    it 'returns the original payload if not encrypted' do
      payload = Temporalio::Api::Common::V1::Payload.new(
        metadata: { 'content-type' => 'application/json' },
        data: '{"test":"data"}'
      )

      result = codec.decode([payload])

      expect(result.size).to eq(1)
      expect(result[0]).to eq(payload)
    end

    it 'raises an error when key_id does not match' do
      payload = Temporalio::Api::Common::V1::Payload.new(
        metadata: { 'content-type' => 'application/json' },
        data: '{"test":"data"}'.b
      )

      encoded = codec.encode([payload])

      different_codec = described_class.new('different-key-id', key)
      
      expect {
        different_codec.decode(encoded)
      }.to raise_error(/Unrecognized key ID/)
    end
  end

  describe 'with default parameters' do
    it 'uses default key_id and key' do
      payload = Temporalio::Api::Common::V1::Payload.new(
        metadata: { 'content-type' => 'application/json' },
        data: '{"test":"data"}'.b
      )

      encoded = default_codec.encode([payload])
      
      expect(encoded[0].metadata['encryption-key-id']).to eq(DEFAULT_KEY_ID.b)
      
      decoded = default_codec.decode(encoded)
      expect(decoded[0].data).to eq(payload.data)
    end
  end

  describe 'encryption and decryption' do
    it 'handles multiple payloads' do
      payload1 = Temporalio::Api::Common::V1::Payload.new(
        metadata: { 'content-type' => 'application/json' },
        data: '{"id": 1}'
      )
      
      payload2 = Temporalio::Api::Common::V1::Payload.new(
        metadata: { 'content-type' => 'application/json' },
        data: '{"id": 2}'
      )

      encoded = codec.encode([payload1, payload2])
      decoded = codec.decode(encoded)

      expect(decoded.size).to eq(2)
      expect(decoded[0].data).to eq(payload1.data)
      expect(decoded[1].data).to eq(payload2.data)
    end
  end
end
