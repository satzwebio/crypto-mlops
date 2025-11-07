# Console
kubectl port-forward svc/minio-service 9001:9001 -n infra &
# Api
kubectl port-forward svc/minio-service 9000:9000 -n infra &

# postgres
kubectl port-forward svc/postgres-service 5432:5432 -n infra &

kubectl port-forward svc/mlflow-service 5000:5000 -n infra &
kubectl port-forward -n infra svc/redis-master 6379:6379 &


kubectl port-forward svc/my-cluster-kafka-bootstrap -n infra 9092:9092 &





kubectl apply -f minio-deployment.yaml

kubectl get pods -n infra

kubectl port-forward svc/minio-service 9001:9001 -n infra

http://localhost:9001

Username: minioadmin
Password: minioadmin123

Click “+ Create Bucket” on the right.
Create the following three buckets:

mlflow-artifacts
feast-feature-store
dvc-storage

------------
kubectl apply -f infra/postgres-deployment.yaml
kubectl get pods -n infra

------------------

PostgreSQL → for MLflow’s backend store (metadata, params, metrics)

MinIO → for artifact storage (models, plots, logs)

kubectl apply -f infra/mlflow-deployment.yaml

kubectl get pods -n infra

kubectl port-forward svc/mlflow-service 5000:5000 -n infra


http://localhost:30500

--------------------

Step 3 — Set Up PostgreSQL + Redis (for Feast feature store)
MLflow and Feast both use SQLAlchemy/Postgres clients — they won’t conflict if we separate databases/schemas.


kubectl get pods -n infra | grep postgres

kubectl exec -it postgres-84ffcd4b46-kwbvv -n infra -- psql -U mlops -d mlopsdb

Step 2: Create a new database for Feast
CREATE DATABASE feastdb;
\l
\q

Step 3: Feast will use this URI
postgresql://mlops:mlops123@postgres-service.infra.svc.cluster.local:5432/feastdb

Step 4 — Install Redis for Feast

helm upgrade --install redis bitnami/redis \
  --namespace infra \
  --set architecture=standalone \
  --set auth.enabled=false \
  --set master.service.type=ClusterIP

Connection URI for Feast:

redis://redis-master.infra.svc.cluster.local:6379


Step 5 — Feast Setup and Configuration
🧠 Architecture Overview

In your setup:

| Purpose           | Store                                      | Backend                                   |
| ----------------- | ------------------------------------------ | ----------------------------------------- |
| **Offline store** | For historical training data               | PostgreSQL (`feastdb`)                    |
| **Online store**  | For real-time lookups during serving       | Redis                                     |
| **Feature repo**  | Your Python/Feast definitions and registry | Local folder (in Git + versioned via DVC) |


Local Development

python -m venv venv
source venv/Scripts/activate      # On Windows Git Bash
# or for PowerShell:
# venv\Scripts\activate

pip install feast[redis,postgres]

pip show feast

mkdir -p feast_repo
cd feast_repo

feast init crypto_features

-------------

Define the Feast Entity and Feature view in example_repo.py

Step 2 — Create Example Data (for initial testing)

mkdir -p feature_repo/data

Go here 
$ pwd   
/c/Users/satzw/OneDrive/Desktop/crypto-mlops/feast_repo/crypto_features

python

and run below

% import pandas as pd
% from datetime import datetime, timedelta
% import numpy as np
% from pathlib import Path

% # Always ensure directory exists
% Path("feature_repo/data").mkdir(parents=True, exist_ok=True)

% symbols = ["BTCUSDT", "ETHUSDT"]
% records = []
% now = datetime.utcnow()

% for s in symbols:
%     for i in range(100):
%         ts = now - timedelta(minutes=i)
%         price = 30000 + np.random.randn() * 1000
%         volume = 1000 + np.random.randn() * 100
%         ma5 = price + np.random.randn() * 10
%         ma10 = price + np.random.randn() * 20
%         vol = abs(np.random.randn())
%         records.append([s, ts, price, volume, ma5, ma10, vol, ts])

% df = pd.DataFrame(records, columns=[
%     "symbol", "event_timestamp", "price", "volume",
%     "price_ma_5", "price_ma_10", "price_volatility", "created"
% ])

% df.to_parquet("feature_repo/data/crypto_prices.parquet")

you will see 2files under data..

feast apply

% feast apply does not materialize data yet; it only registers metadata.
% It executes your Python files to find all Entity and FeatureView objects.
% It reads the configuration from feature_store.yaml to know where to deploy features.
% After feast apply, your project knows:
% Which entities exist
% Which features exist
% Where offline/online stores are
% How to materialize and serve features later

# Under Feast_offline DB, create a table crypto_process
# Refer infra notes for how to exec in to psql client pod

CREATE TABLE crypto_proces (
    symbol TEXT,
    price FLOAT,
    volume FLOAT,
    timestamp TIMESTAMP
);

This table — crypto_proces — is your offline store source for Feast.

kubectl port-forward svc/postgres-service 5432:5432 -n infra


$ python ./load_crypto_process.py 

Run this to verify, its loaded

kubectl exec -it -n infra $(kubectl get pod -n infra -l app=postgres -o name) -- \
psql -U mlops -d feast_offline -c "SELECT * FROM crypto_proces LIMIT 5;"

----------------

Feast moves data from your offline store (Postgres) into your online store (Redis) — so your model can serve live features.


kubectl port-forward -n infra svc/redis-master 6379:6379

To validate locally
<!-- $ python
Python 3.12.8 (tags/v3.12.8:2dc476b, Dec  3 2024, 19:30:04) [MSC v.1942 64 bit (AMD64)] on win32
Type "help", "copyright", "credits" or "license" for more information.
Ctrl click to launch VS Code Native REPL
>>> import redis
>>> r = redis.Redis(host='localhost', port=6379)
>>> print(r.ping())
True -->

# Update the crypto source to Postgresql spource in example_repo.py by adding below
<!-- FileSource is fine for local lookups, but doesn’t support all the SQL-like filtering and joining logic needed for production pipelines. -->

% from feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source import PostgreSQLSource

% crypto_source = PostgreSQLSource(
%     name="crypto_source",
%     query="SELECT * FROM crypto_proces",
%     timestamp_field="event_timestamp",
%     created_timestamp_column="created",
% )

Update the online connection setting as 
connection_string: "localhost:6379"

now remove the data/registry.db
<!-- % registry.db is Feast’s local registry —
% it’s like a metadata database that stores what Feast knows about:
% your data sources
% your feature views
% your entities
% your project configuration -->

then run `feast apply`

Now Materialize feature data to Redis

feast materialize-incremental $(date +%Y-%m-%dT%H:%M:%S)


# Check feast read your latest features from Redis(Online Store)

Run feast_read_test in python `python`
cd feast_repo/crypto_features/feature_repo/
python ./feast_read_test.py


Why Feast?

Feast ensures that features in the online store are consistent, transformed, and incrementally updated from the offline store. It handles point-in-time correctness, feature versioning, and reproducibility, which a simple cron job cannot.
This makes real-time model serving reliable without custom pipelines for feature computation or updates.

------------------------

Model Training + DVC Setup

1. DVC tracks which feature dataset version was used
2. MLFlow logs model performance
3. We can always reproduce a specific model with same data version.


Step 1: Initialize DVC in your repo

pip install "dvc[s3]"
dvc --version



git init # If not initialized earlier
dvc init

git add .dvc .dvcignore
git commit -m "Initialize DVC for data and model versioning"

# Create user in minio  # this is not required
# Create access amd secret key for the user in minio - 
    i4uQb2rjeKHPNRILXU4u
    15woTgEJswI9yaVRsygK9gQ1V6UJdYUGZGrSwVK0

dvc remote add -d minio s3://dvc-storage

dvc remote modify minio endpointurl http://localhost:9000   # 9000 is the API port, 9001 is the console
<!-- dvc remote modify minio access_key_id i4uQb2rjeKHPNRILXU4u
dvc remote modify minio secret_access_key 15woTgEJswI9yaVRsygK9gQ1V6UJdYUGZGrSwVK0 -->
dvc remote modify minio use_ssl false

dvc remote list

Track dataset with DVC
dvc add feast_repo/crypto_features/feature_repo/data/crypto_prices.parquet

This will:
Create a .dvc tracking file beside your dataset (e.g. crypto_prices.parquet.dvc).
Add a hash-based reference to .dvc/.

dvc push


To check whether a simple experiment is reachable to MLFLOW and minio

Run this in local

$ export MLFLOW_TRACKING_URI="http://localhost:5000"
$ export MLFLOW_S3_ENDPOINT_URL="http://localhost:9000"
$ export AWS_ACCESS_KEY_ID="minioadmin"
$ export AWS_SECRET_ACCESS_KEY="minioadmin123"

pip install mlflow

# Check MLFlow connection by running this python snippet
python ./localhost-mlflow.py 

<!-- import mlflow, tempfile, os

mlflow.set_experiment("local-test")

with mlflow.start_run():
    mlflow.log_param("lr", 0.05)
    mlflow.log_metric("accuracy", 0.93)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("Test artifact from local MLflow client")
        temp_path = f.name
    mlflow.log_artifact(temp_path)
    print("✅ Logged successfully to MLflow + MinIO") -->


# Now you will see an experiment in mlflow UI also under minio

# lets cross check this in postgresql
$ kubectl exec -it postgres-6675498649-dkq4m -n infra -- psql -U mlops -d mlopsdb
psql (16.10 (Debian 16.10-1.pgdg13+1))
Type "help" for help.

mlopsdb=# \dt
mlopsdb=# SELECT experiment_id, name, artifact_location FROM experiments;
 experiment_id |        name        |    artifact_location    
---------------+--------------------+-------------------------
             0 | Default            | s3://mlflow-artifacts/0
             1 | crypto_price_model | s3://mlflow-artifacts/1
             2 | test-artifacts     | s3://mlflow-artifacts/2
             3 | local-test         | s3://mlflow-artifacts/3
(4 rows)

mlopsdb=# SELECT run_uuid, experiment_id, status, lifecycle_stage FROM runs LIMIT 5;
             run_uuid             | experiment_id |  status  | lifecycle_stage 
----------------------------------+---------------+----------+-----------------
 2ada338c48d2447db8b33110014a8ebf |             1 | FINISHED | active
 97f5b6a838364259820b4f387488b1bb |             1 | FINISHED | active
 b59177b98ef3496f8f4560558f656952 |             1 | FINISHED | active
 61d85d32d4e845b5a6b2f8f267d30749 |             1 | FINISHED | active
 5847baaa387b4289a5b30b34d53575b3 |             1 | FINISHED | active
(5 rows)

mlopsdb=#

---------------------

# Install Kafka Strimzi

# Apply Strimzi cluster operator (uses CRDs)
kubectl apply -f https://strimzi.io/install/latest?namespace=infra -n infra

kubectl apply -f infra/kafka-cluster-kraft.yaml

# This defines how many brokers (Kafka nodes) to run
kubectl apply -f infra/kafka-nodepool.yaml
kubectl get pods -n infra -l strimzi.io/cluster=my-cluster

# create a topic named crypto-prices, which will hold real-time price messages coming from the WebSocket.
kubectl apply -f infra/kafka-topic.yaml


A Kafka Topic is like a streaming channel — where data is continuously published and consumed.
Run this to create a temporary Kafka producer pod:
kubectl run kafka-producer -ti --image=quay.io/strimzi/kafka:latest-kafka-4.0.0 --namespace infra --rm=true --restart=Never -- \
  bin/kafka-console-producer.sh --bootstrap-server my-cluster-kafka-bootstrap.infra.svc.cluster.local:9092 --topic crypto-prices

When the prompt appears, type a few messages manually:
BTC,70000
ETH,3900
DOGE,0.22


Next, create a consumer to verify it worked:
kubectl run kafka-consumer -ti --image=quay.io/strimzi/kafka:latest-kafka-4.0.0 --namespace infra --rm=true --restart=Never -- \
  bin/kafka-console-consumer.sh --bootstrap-server my-cluster-kafka-bootstrap.infra.svc.cluster.local:9092 --topic crypto-prices --from-beginning

You should see your messages printed back


[WebSocket feed]
       ↓
 [Kafka producer container]
       ↓
  Kafka topic: crypto-prices
       ↓
 [Kafka consumer → MinIO parquet]

Python WebSocket → Kafka producer code

Run the script
python websocket_kafka_producer.py

1️⃣ What we did in the Kafka setup

Created a Kafka cluster with Strimzi in Kubernetes (my-cluster)

Single broker, ephemeral storage (dev/testing).

Added external NodePort listener to allow your local machine to connect.

Port-forwarded the Kafka external listener to localhost

kubectl port-forward svc/my-cluster-kafka-external-bootstrap -n infra 9094:9094


This allows your Python script running on your desktop to connect to the in-cluster Kafka as if it’s local.

Workaround for advertised listeners

Kafka brokers advertise their internal IPs by default (172.18.x.x) to clients.

Your producer couldn’t reach the broker because it tried the internal cluster IP from your local machine.

Fix: updated the Kafka listener config in Strimzi to advertise localhost:9094.

This ensures all connections from your local script stay on localhost.

2️⃣ What we achieved

✅ Python script connects to Binance WebSocket.

✅ Messages are sent to Kafka topic crypto-prices.

✅ No more Failed to resolve host errors.

3️⃣ Production considerations

Do not use ephemeral storage → use persistent volumes (PVCs).

Do not use NodePort for external clients → use LoadBalancer, Ingress, or a Kafka REST Proxy.

Security: enable TLS + SASL for authentication between producers/consumers and Kafka.

High availability: run multiple brokers & Zookeeper/NodePools for redundancy.

Monitoring: integrate Kafka metrics (Prometheus + Grafana).

4️⃣ How to consume these messages in a test pod

You can create a temporary Kafka consumer pod in the same namespace:

kubectl run kafka-test-consumer -n infra -it --rm --image=strimzi/kafka:0.46.0-kafka-4.0.0 --restart=Never -- \
  kafka-console-consumer.sh \
  --bootstrap-server my-cluster-kafka-bootstrap:9092 \
  --topic crypto-prices \
  --from-beginning


The pod will attach to your cluster Kafka.

You’ll see all messages your Python producer sent.

Good for testing / debugging before moving to your MinIO consumer.

