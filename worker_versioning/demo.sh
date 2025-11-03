#!/bin/sh

# Constants
WORKER_NAMESPACE="temporal-workers"
TAG=$(date +%Y%m%d-%H%M%S)
TASK_QUEUE="MoneyTransfer-$TAG"

pause_if_step() {
  if [ "$STEP_MODE" = true ]; then
    echo "Press any key to continue...\\n"
    read -n 1 -s
  fi
}

start_minikube() {
  echo "🚀 Starting minikube..."
  minikube status > /dev/null 2>&1 || minikube start
  echo "┌────────────────────────────────────────────────────────────────────────────────────────────┐"
  echo "│ 💡 Observe pods: k9s -n $WORKER_NAMESPACE                                                   │"
  echo "└────────────────────────────────────────────────────────────────────────────────────────────┘"
  pause_if_step
}

cleanup_existing_deployment() {
  echo "🧹 Cleaning up existing deployments"
  if kubectl get pods -l temporal.io/deployment-name=money-transfer-worker-deployment -n $WORKER_NAMESPACE 2>/dev/null | grep -q "Running\|Pending\|ContainerCreating"; then
    
    # Delete the existing deployment to make the demo idempotent
    kubectl delete -f temporal-worker-deployment.yaml -n $WORKER_NAMESPACE --ignore-not-found=true
    kubectl delete pods --all -n $WORKER_NAMESPACE --force
    
    # Wait for all pods to be terminated
    echo "⏳ Waiting for containers to terminate (this may take a moment)..."
    kubectl wait --for=delete pods -l temporal.io/deployment-name=money-transfer-worker-deployment -n $WORKER_NAMESPACE --timeout=60s 2>/dev/null || true
  fi
  
  # Terminate all system workflows for the deployment
  temporal workflow delete --query "TemporalNamespaceDivision=\"TemporalWorkerDeployment\"" --yes 2>/dev/null || true
  temporal workflow terminate --query "WorkflowType=\"AccountTransferWorkflow\"" --yes 2>/dev/null || true
  temporal workflow delete --query "WorkflowType=\"AccountTransferWorkflow\"" --yes 2>/dev/null || true
  pause_if_step
}

install_temporal_worker_controller() {
  # Check if helm is installed
  if ! command -v helm > /dev/null 2>&1; then
    echo "❌ helm is not installed. Please install helm first."
    exit 1
  fi
  
  # Check if chart already exists
  if helm list -n $WORKER_NAMESPACE | grep -q temporal-worker-controller; then
    echo "✅ Temporal Worker Controller already installed, skipping..."
  else
    echo "📦 Installing Temporal Worker Controller via Helm..."
    # Create namespace for controller
    kubectl create namespace $WORKER_NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    
    # Install the controller
    helm install temporal-worker-controller \
      oci://docker.io/temporalio/temporal-worker-controller \
      --namespace $WORKER_NAMESPACE --create-namespace
  fi
  
  echo "⏳ Waiting for Temporal Worker Controller to be ready..."
  kubectl wait --for=condition=available deployment/temporal-worker-controller-manager -n $WORKER_NAMESPACE --timeout=30s || exit 1
  pause_if_step
}

build_image() {
  echo "🐳 Building Worker image..."
  eval $(minikube docker-env)
  TAG_V1="${TAG}-v1"
  echo "┌────────────────────────────────────────────────────────────────────────────────────────────┐"
  echo "│ 📋 Using tag: $TAG_V1 (Note, the tag will be used as the Deployment Version)    │"
  echo "└────────────────────────────────────────────────────────────────────────────────────────────┘"
  if docker image inspect money-transfer-worker > /dev/null 2>&1; then
    docker build --quiet -t money-transfer-worker:$TAG_V1 -t money-transfer-worker:latest -f Dockerfile . 2>&1 | grep -v "What's next:"
  else
    docker build -t money-transfer-worker:$TAG_V1 -t money-transfer-worker:latest -f Dockerfile . 2>&1 | grep -v "What's next:"
  fi
  pause_if_step
}

setup_temporal_connection() {
  echo "🔗 Setting up TemporalConnection..."
  echo
  echo "👉 Inspect config: $(pwd)/temporal-connection.yaml"
  echo

  kubectl apply -f temporal-connection.yaml -n $WORKER_NAMESPACE
  pause_if_step
}

deploy_worker_deployment_config() {
  echo "⚙️  Deploying TemporalWorkerDeployment..."
  echo
  echo "👉 Inspect config: $(pwd)/temporal-worker-deployment.yaml"
  echo
  
  # Replace placeholders with actual values
  sed -e "s/PLACEHOLDER_IMAGE/money-transfer-worker:$TAG_V1/g" \
      -e "s/PLACEHOLDER_TASK_QUEUE/$TASK_QUEUE/g" \
      temporal-worker-deployment.yaml | kubectl apply -f - -n $WORKER_NAMESPACE

  echo "👀 You should now see 3 worker pods with $TAG_V1 in their names in k9s"

  pause_if_step
}

start_workflows() {
  WORKFLOW_COUNT=10
  echo "🚀 Starting $WORKFLOW_COUNT workflows..."

  if [ "$MODE" = "cloud" ]; then
    ENV_FLAG="--env ${TEMPORAL_ENV}"
  else
    ENV_FLAG=""
  fi
  
  for i in $(seq 1 $WORKFLOW_COUNT); do
    temporal workflow start \
      $ENV_FLAG \
      --type AccountTransferWorkflow \
      --task-queue $TASK_QUEUE \
      --workflow-id TRANSFER-VERSIONING-$i \
      --input '{"amount": 45, "fromAccount": "account1", "toAccount": "account2"}' > /dev/null 2>&1 || echo "Error starting workflow $i" >&2
  done
  echo "✅ Started $WORKFLOW_COUNT workflows"

  echo
  echo "🔍 You can observe the Build ID on the newly started workflows in the Temporal UI"
  show_info
  pause_if_step
}

show_info() {
  echo "┌────────────────────────────────────────────────────────────────────────────────────────────┐"
  if [ "$MODE" = "cloud" ]; then
    echo "│ 🌐 View workflows:	https://cloud.temporal.io/namespaces/${TEMPORAL_NAMESPACE}/workflows	     │"
  else
    echo "│ 🌐 View workflows:	http://localhost:8233/namespaces/default/workflows	             │"
  fi
  echo "└────────────────────────────────────────────────────────────────────────────────────────────┘"
}

patch_deployment() {
  echo "🐳 Building new Worker image..."
  eval $(minikube docker-env)
  TAG_V2="${TAG}-v2"
  echo "📋 Using new tag: $TAG_V2"
  docker build --quiet -t money-transfer-worker:$TAG_V2 -f Dockerfile . 2>&1 | grep -v "What's next:"
  
  echo "🔄 Press any key to patch deployment with the new image..."
  read -n 1 -s

  echo
  echo "kubectl patch temporalworkerdeployment money-transfer-worker-deployment --type='json' -p='[{\"op\":\"replace\",\"path\":\"/spec/template/spec/containers/0/image\",\"value\":\"money-transfer-worker:'$TAG_V2'\"}]' -n $WORKER_NAMESPACE"
  echo
  kubectl patch temporalworkerdeployment money-transfer-worker-deployment --type='json' -p='[{"op":"replace","path":"/spec/template/spec/containers/0/image","value":"money-transfer-worker:'$TAG_V2'"}]' -n $WORKER_NAMESPACE
  
  echo
  echo "👀 You should now see 3 more worker pods with $TAG_V2 in their names in k9s"
  echo "🔄 Observe workflows slowly upgrade to $TAG_V2 (tip: the Build ID is visible from search attributes as well as on individual workflow page)"
  
  echo "┌────────────────────────────────────────────────────────────────────────────────────────────┐"
  echo "│ 🌐 View Worker Deployments: http://localhost:8233/namespaces/default/worker-deployments     │"
  echo "└────────────────────────────────────────────────────────────────────────────────────────────┘"

  echo "🔄 Press any key to complete the demo..."
  read -n 1 -s
}

# Parse arguments
MODE="local"
FOLLOW_LOGS=false
ENCRYPT_PAYLOADS="false"
STEP_MODE=false

for arg in "$@"; do
  case $arg in
    --cloud)
      MODE="cloud"
      ;;
    --follow)
      FOLLOW_LOGS=true
      ;;
    --encrypt)
      ENCRYPT_PAYLOADS="true"
      ;;
    --step)
      STEP_MODE=true
      ;;
  esac
done

check_kubectl() {
  if ! command -v kubectl > /dev/null 2>&1; then
    echo "❌ kubectl is not installed. Please install kubectl first."
    exit 1
  fi
}

check_directory() {
  if [ "$(basename "$(pwd)")" != "worker_versioning" ]; then
    echo "❌ This script must be run from the 'worker_versioning' directory."
    echo "Current directory: $(pwd)"
    echo "Please cd to the 'worker_versioning' directory and run the script again."
    exit 1
  fi
}

# Main execution
check_directory
check_kubectl
start_minikube
cleanup_existing_deployment
install_temporal_worker_controller
build_image
setup_temporal_connection
deploy_worker_deployment_config
start_workflows
patch_deployment


# Todo:
# Report doc error: temporal.io/worker-deployment -> temporal.io/deployment-name
# Ref: https://github.com/temporalio/temporal-worker-controller/blob/dc164cae995407cbce3c829daea4968b9603acb7/internal/k8s/deployments.go#L30
