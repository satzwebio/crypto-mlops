#!/usr/bin/env bash
set -e

# ============================
# CONFIGURATION
# ============================
KIND_CLUSTER_NAME="mlops-cluster"
NAMESPACE_INFRA="infra"
NAMESPACE_PIPELINES="pipelines"
NAMESPACE_KSERVE="kserve"

echo "🚀 Setting up local MLOps infrastructure on Kind cluster: ${KIND_CLUSTER_NAME}"

# --- Create cluster if not exists ---
if ! kind get clusters | grep -q "${KIND_CLUSTER_NAME}"; then
  echo "🌱 Creating Kind cluster..."
  kind create cluster --name ${KIND_CLUSTER_NAME} --config <<EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
    extraPortMappings:
      - containerPort: 30080
        hostPort: 30080
      - containerPort: 30081
        hostPort: 30081
      - containerPort: 30082
        hostPort: 30082
      - containerPort: 30083
        hostPort: 30083
EOF
else
  echo "✅ Kind cluster already exists."
fi

# --- Create namespaces ---
kubectl create ns ${NAMESPACE_INFRA} --dry-run=client -o yaml | kubectl apply -f -
kubectl create ns ${NAMESPACE_PIPELINES} --dry-run=client -o yaml | kubectl apply -f -
kubectl create ns ${NAMESPACE_KSERVE} --dry-run=client -o yaml | kubectl apply -f -

# ============================
# INSTALL MINIO
# ============================
echo "📦 Installing MinIO..."
helm repo add minio https://charts.min.io/
helm repo update
helm upgrade --install minio minio/minio \
  --namespace ${NAMESPACE_INFRA} \
  --set mode=standalone,rootUser=admin,rootPassword=password123,replicas=1,resources.requests.memory=512Mi \
  --set service.type=NodePort \
  --set service.nodePort=30080

# ============================
# INSTALL POSTGRES
# ============================
echo "🐘 Installing Postgres..."
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm upgrade --install postgres bitnami/postgresql \
  --namespace ${NAMESPACE_INFRA} \
  --set auth.postgresPassword=postgres,primary.service.type=NodePort,primary.service.nodePorts.postgresql=30081

# ============================
# INSTALL REDIS
# ============================
helm upgrade --install redis bitnami/redis \
  --namespace ${NAMESPACE_INFRA} \
  --set auth.enabled=false \
  --set master.service.type=ClusterIP \
  --wait


# ============================
# INSTALL KAFKA
# ============================
echo "📨 Installing Kafka..."
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm upgrade --install kafka bitnami/kafka \
  --namespace ${NAMESPACE_INFRA} \
  --set replicaCount=1,zookeeper.enabled=true,listeners.client.protocol=PLAINTEXT,service.type=NodePort,service.nodePorts.client=30083

# ============================
# INSTALL MLFLOW
# ============================
echo "📊 Deploying MLflow tracking server..."
cat <<EOF | kubectl apply -n ${NAMESPACE_INFRA} -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mlflow
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mlflow
  template:
    metadata:
      labels:
        app: mlflow
    spec:
      containers:
        - name: mlflow
          image: cr.flyte.org/ghcr.io/mlflow/mlflow:2.6.0
          command: ["mlflow", "server"]
          args: [
            "--backend-store-uri", "postgresql://postgres:postgres@postgres.${NAMESPACE_INFRA}.svc.cluster.local:5432/postgres",
            "--default-artifact-root", "s3://mlflow/",
            "--host", "0.0.0.0",
            "--port", "5000"
          ]
          env:
            - name: AWS_ACCESS_KEY_ID
              value: admin
            - name: AWS_SECRET_ACCESS_KEY
              value: password123
            - name: MLFLOW_S3_ENDPOINT_URL
              value: http://minio.${NAMESPACE_INFRA}.svc.cluster.local:9000
          ports:
            - containerPort: 5000
---
apiVersion: v1
kind: Service
metadata:
  name: mlflow
spec:
  type: NodePort
  ports:
    - port: 5000
      targetPort: 5000
      nodePort: 30084
  selector:
    app: mlflow
EOF

# ============================
# INSTALL KSERVE (for BentoML serving)
# ============================
echo "🤖 Installing KServe..."
kubectl apply -f https://github.com/kserve/kserve/releases/download/v0.12.1/kserve.yaml
kubectl wait --for=condition=Available deployment --all -n kserve --timeout=180s || true

# ============================
# INSTALL KUBEFLOW PIPELINES (standalone)
# ============================
echo "🧩 Installing Kubeflow Pipelines (standalone)..."
kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/cluster-scoped-resources?ref=2.0.0"
kubectl wait --for=condition=established crd/pipelines.kubeflow.org --timeout=180s
kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/env/platform-agnostic?ref=2.0.0"
kubectl rollout status deployment/ml-pipeline -n kubeflow --timeout=300s || echo "⚠️  Kubeflow rollout may need retry."

echo "✅ Infrastructure deployed successfully!"

echo "-------------------------------------------"
echo "Services available locally:"
echo "MinIO UI       -> http://localhost:30080"
echo "Postgres       -> localhost:30081"
echo "Redis          -> localhost:30082"
echo "Kafka Broker   -> localhost:30083"
echo "MLflow UI      -> http://localhost:30084"
echo "Kubeflow UI    -> http://localhost:<kubeflow_port>"
echo "-------------------------------------------"
