# frozen_string_literal: true

require 'temporalio/client'
require 'temporalio/worker'
require 'logger'
require_relative 'workflows/account_transfer_workflow'
require_relative 'workflows/account_transfer_workflow_scenarios'
require_relative 'activities/validate_activity'
require_relative 'activities/withdraw_activity'
require_relative 'activities/deposit_activity'
require_relative 'activities/send_notification_activity'
require_relative 'activities/undo_withdraw_activity'
require_relative 'security/encryption_codec'

class Worker
  def run
    logger.info('Ruby money transfer worker starting...')

    Temporalio::Worker.new(
      client: temporal_client,
      task_queue: task_queue,
      workflows: [
        Workflows::AccountTransferWorkflow,
        Workflows::AccountTransferWorkflowScenarios
      ],
      activities: [
        Activities::ValidateActivity,
        Activities::WithdrawActivity,
        Activities::DepositActivity,
        Activities::SendNotificationActivity,
        Activities::UndoWithdrawActivity
      ],
      workflow_payload_codec_thread_pool: Temporalio::Worker::ThreadPool.default
    ).run
  end

  private

  def logger
    @logger ||= Logger.new($stdout, level: :info)
  end

  def temporal_client
    @client ||= begin
      options = {
        logger: logger
      }.tap do |options|
        options.merge!(tls_options) if using_tls?
        options.merge!(encryption_options) if encrypt_payloads?
      end
      Temporalio::Client.connect(temporal_address, temporal_namespace, **options)
    end
  end

  def tls_options
    if api_key
      {
        tls: true,
        api_key: api_key,
        rpc_metadata: { 'temporal-namespace' => temporal_namespace }
      }
    elsif cert_path && key_path
      {
        tls: Temporalio::Client::Connection::TLSOptions.new(
          client_cert: File.read(cert_path),
          client_private_key: File.read(key_path)
        )
      }
    else
      {}
    end
  end

  def encryption_options
    return {} unless encrypt_payloads?

    {
      data_converter: Temporalio::Converters::DataConverter.new(
        payload_codec: Security::EncryptionCodec.new
      )
    }
  end

  def temporal_address
    ENV.fetch('TEMPORAL_ADDRESS', 'localhost:7233')
  end

  def temporal_namespace
    ENV.fetch('TEMPORAL_NAMESPACE', 'default')
  end

  def task_queue
    ENV.fetch('TEMPORAL_MONEYTRANSFER_TASKQUEUE', 'MoneyTransfer')
  end

  def api_key
    ENV['TEMPORAL_API_KEY']
  end

  def cert_path
    ENV['TEMPORAL_CERT_PATH']
  end

  def key_path
    ENV['TEMPORAL_KEY_PATH']
  end

  def using_tls?
    api_key || (cert_path && key_path)
  end

  def encrypt_payloads?
    ENV['ENCRYPT_PAYLOADS']&.downcase == 'true'
  end
end

Worker.new.run if __FILE__ == $PROGRAM_NAME
