import fs from 'fs/promises';
import type * as client from '@temporalio/client';
import type { RuntimeOptions, WorkerOptions } from '@temporalio/worker';

// Common set of connection options that can be used for both the client and worker connections.
export type ConnectionOptions = Pick<client.ConnectionOptions, 'tls' | 'address'>;

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

  let tls: ConnectionOptions['tls'] = undefined;
  if (process.env.TEMPORAL_CERT_PATH && process.env.TEMPORAL_KEY_PATH) {
    const crt = await fs.readFile(getenv('TEMPORAL_CERT_PATH'));
    const key = await fs.readFile(getenv('TEMPORAL_KEY_PATH'));

    tls = { clientCertPair: { crt, key } };
    console.info('🤖: Connecting to Temporal Cloud ⛅');
  } else {
    console.info('🤖: Connecting to Local Temporal');
  }

  return {
    address,
    tls,
  };
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