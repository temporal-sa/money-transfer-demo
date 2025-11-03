# Worker Versioning Demo

Demonstrates Temporal worker versioning using the Temporal Operator in a Kubernetes environment. This demo shows how to safely deploy new versions of workers and migrate workflows between versions.

## Prerequisites

- `kubectl` installed
- `minikube` installed
- Docker installed
- Temporal CLI installed
- Temporal Worker Controller installed
- `k9s` (optional, for monitoring)

## Setup

If using asdf version manager, install all required tool versions:
```bash
asdf install
```

## Running the Demo

### Basic Usage

```bash
./demo.sh [--cloud] [--follow] [--encrypt] [--step]
```

### Options

- `--cloud` - Connect to Temporal Cloud (requires `setcloudenv.sh` configuration)
- `--follow` - Watch deployment scaling and logs in real-time
- `--encrypt` - Enable payload encryption
- `--step` - Pause after each step and wait for user input to continue

### Examples

```bash
# Local Temporal server
./demo.sh

# Temporal Cloud with log following
./demo.sh --cloud --follow

# Local with encryption and step-by-step execution
./demo.sh --encrypt --step
```

## Demo Flow

1. **Environment Setup**
   - Starts minikube cluster
   - Installs Temporal Worker Controller
   - Creates necessary namespaces

2. **Worker Deployment**
   - Builds worker Docker image
   - Sets up TemporalConnection resource
   - Deploys initial worker version (v1.0)

3. **Version Migration**
   - Deploys new worker version (v2.0)
   - Demonstrates safe version transitions
   - Shows workflow compatibility between versions

4. **Monitoring & Validation**
   - Tracks worker scaling
   - Monitors workflow execution
   - Validates version migration success

## Temporal Cloud Configuration

For Temporal Cloud usage, copy and configure the environment file:
```bash
cp ../setcloudenv.example ../setcloudenv.sh
```

Edit `setcloudenv.sh` with your Temporal Cloud credentials:
```bash
# Using mTLS
export TEMPORAL_ADDRESS=<namespace>.<accountID>.tmprl.cloud:7233
export TEMPORAL_NAMESPACE=<namespace>.<accountID>
export TEMPORAL_CERT_PATH="/path/to/cert.pem"
export TEMPORAL_KEY_PATH="/path/to/key.key"

# Using API Keys
export TEMPORAL_ADDRESS=<region>.<cloud_provider>.api.temporal.io:7233
export TEMPORAL_NAMESPACE=<namespace>.<accountID>
export TEMPORAL_API_KEY=<api_key>
```

## Monitoring

- **Temporal UI**: 
  - Local: http://localhost:8233
  - Cloud: Your Temporal Cloud namespace UI
- **Kubernetes Pods**: `kubectl get pods -n money-transfer` or `k9s -n money-transfer`
- **Worker Logs**: `kubectl logs -f deployment/money-transfer-worker -n money-transfer`

## Cleanup

To clean up the demo environment:
```bash
minikube delete
```

## Key Concepts Demonstrated

- **Worker Versioning**: Safe deployment of new worker versions
- **Build ID Management**: Tracking and managing worker build identifiers
- **Version Compatibility**: Ensuring workflows work across versions
- **Kubernetes Integration**: Using Temporal Operator for worker management
- **Zero-Downtime Deployment**: Seamless version transitions