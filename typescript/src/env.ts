import fs from 'fs/promises';
import type * as client from '@temporalio/client';
import type { RuntimeOptions, WorkerOptions } from '@temporalio/worker';

// Common set of connection options that can be used for both the client and worker connections.
export type ConnectionOptions = Pick<client.ConnectionOptions, 'tls' | 'address'> & { apiKey?: string }; //Set API key as string due to type compatibility

export function getenv(key: string, defaultValue?: string): string {
  const value = process.env[key];
  if (!value) {
    if (defaultValue != null) {
      return defaultValue;
    }
    throw new Error(`missing env var: ${key}`);
  }
  return value;
}

export async function getConnectionOptions(): Promise<ConnectionOptions> {
  const address = getenv('TEMPORAL_ADDRESS', 'localhost:7233');
  const options: ConnectionOptions = { address };

  let tls: ConnectionOptions['tls'] = undefined;
  
  //First check for API Key
  if (process.env.TEMPORAL_API_KEY) {
    console.info('🤖: Connecting to Temporal Cloud using API key ⛅');
    options.apiKey = getenv('TEMPORAL_API_KEY');
    options.tls = true; // Set tls to true when using API keys for Temporal Cloud
  }
  //Fall back to mTLS certs if API key not present
  else if (process.env.TEMPORAL_CERT_PATH && process.env.TEMPORAL_KEY_PATH) {
    try {
      console.info(`🤖: Attempting to read certs from: ${process.env.TEMPORAL_CERT_PATH}`);
      const crt = await fs.readFile(getenv('TEMPORAL_CERT_PATH'));
      const key = await fs.readFile(getenv('TEMPORAL_KEY_PATH'));

      tls = { clientCertPair: { crt, key } };
      options.tls = tls;
      console.info('🤖: Connecting to Temporal Cloud using mTLS Certs ⛅');
    } catch (error) {
      console.error('❌ Error reading certificate files:', error);
      console.info('🤖: Falling back to Local Temporal connection');
    }
  } else {
    console.info('🤖: Certificate paths not found, connecting to Local Temporal');
  }

  return options;
}

export function getWorkflowOptions(): Pick<WorkerOptions, 'workflowBundle' | 'workflowsPath'> {
  const workflowBundlePath = getenv('WORKFLOW_BUNDLE_PATH', 'lib/workflow-bundle.js');

  if (workflowBundlePath && env == 'production') {
    return { workflowBundle: { codePath: workflowBundlePath } };
  } else {
    return { workflowsPath: require.resolve('./workflows/index') };
  }
}

export function getTelemetryOptions(): RuntimeOptions {
  const metrics = getenv('TEMPORAL_WORKER_METRIC', 'PROMETHEUS');
  const port = getenv('TEMPORAL_WORKER_METRICS_PORT', '9464');
  let telemetryOptions = {};

  switch (metrics) {
    case 'PROMETHEUS':
      const bindAddress = getenv('TEMPORAL_METRICS_PROMETHEUS_ADDRESS', `0.0.0.0:${port}`);
      telemetryOptions = {
        metrics: {
          prometheus: {
            bindAddress,
          },
        },
      };
      console.info('🤖: Prometheus Metrics 🔥', bindAddress);
      break;
    case 'OTEL':
      telemetryOptions = {
        metrics: {
          otel: {
            url: getenv('TEMPORAL_METRICS_OTEL_URL'),
            headers: {
              'api-key': getenv('TEMPORAL_METRICS_OTEL_API_KEY'),
            },
          },
        },
      };
      console.info('🤖: OTEL Metrics 📈');
      break;
    default:
      console.info('🤖: No Metrics');
      break;
  }

  return { telemetryOptions };
}

export const namespace = getenv('TEMPORAL_NAMESPACE', 'default');
export const taskQueue = getenv('TEMPORAL_MONEYTRANSFER_TASKQUEUE', 'MoneyTransfer');
export const env = getenv('NODE_ENV', 'development');

// Encryption
export const encryptPayloads = getenv('ENCRYPT_PAYLOADS', 'false');
export const encryptKey = getenv('ENCRYPT_KEY', 'sa-rocks!sa-rocks!sa-rocks!yeah!');