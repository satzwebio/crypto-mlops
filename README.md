# Crypto MLOps Platform

> Status: In progress — this project is actively being developed and refined.

This repository showcases a portable, end-to-end MLOps setup for crypto data using an ephemeral Kubernetes-based infrastructure. The goal is simple: create a realistic data platform in minutes, use it for streaming, feature engineering, experiment tracking, and model versioning, and then destroy it just as easily.

This is an excellent example of a project that can be used for demos, interviews, hackathons, and portfolio work because it demonstrates both engineering and platform thinking.

## Why this project exists

Modern ML systems are not just about training a model. They also require:

- reliable data ingestion
- streaming pipelines
- feature storage and serving
- experiment tracking
- artifact/version management
- reproducible infrastructure

This project brings those pieces together in a compact and reusable way.

## What the project demonstrates

The stack shows a full flow for crypto market data:

1. A Binance WebSocket stream produces live market events.
2. The events are forwarded to Kafka.
3. Data is stored and processed through a lightweight MLOps platform.
4. Features can be registered and served with Feast.
5. Experiments and model artifacts are tracked with MLflow and DVC.

In short, this repository is a practical blueprint for building an ML platform that can be spun up quickly and torn down without leaving behind expensive or persistent infrastructure.

## Architecture overview

```text
Binance WebSocket
      ↓
   Kafka
      ↓
  Consumers / pipelines
      ↓
Postgres / MinIO / Redis
      ↓
Feast + MLflow + DVC
```

### Core components

- Kafka: real-time event streaming
- MinIO: object storage for artifacts and datasets
- PostgreSQL: metadata and relational storage
- Redis: online feature store support
- MLflow: experiment tracking and model artifact logging
- Feast: feature definitions and serving
- DVC: dataset and model versioning
- Kind + Kubernetes: ephemeral local infrastructure

## Repository structure

- [setup_infra.sh](setup_infra.sh): provisions a local Kind-based infrastructure stack
- [infra](infra): Kubernetes manifests and deployment definitions
- [jobs](jobs): producer and consumer jobs for streaming data
- [feast](feast): Feast feature definitions and repository configuration
- [test](test): lightweight validation scripts for MLflow and local checks
- [load_crypto_process.py](load_crypto_process.py): example loader for moving data into Postgres

## Quick start

### Prerequisites

Make sure you have the following installed:

- Docker
- Kind
- kubectl
- Helm
- Python 3.10+

### 1. Provision the infrastructure

From the repository root, run:

```bash
./setup_infra.sh
```

This script creates a local Kubernetes cluster and installs the services needed for the MLOps workflow.

### 2. Access the services

Once the cluster is up, you can access the local services through port-forwarding or the exposed local ports defined in the setup script.

Typical services include:

- MinIO UI
- MLflow UI
- PostgreSQL
- Redis
- Kafka broker

### 3. Run the data flow

The repository includes example producer and consumer components under [jobs](jobs). These can be used to stream crypto price events and validate the ingestion pipeline.

### 4. Tear it down

Because this is designed to be ephemeral, you can remove the whole environment with:

```bash
kind delete cluster --name mlops-cluster
```

## Why this is valuable for employers

This project is strong for professional portfolios because it shows that you can think beyond a single notebook or script. It demonstrates:

- cloud-native deployment skills
- infrastructure as code mindset
- event-driven architecture
- MLOps practices
- practical experience with modern data tooling

It is also highly adaptable. The same pattern can be reused for other domains such as e-commerce, IoT, logistics, or finance.

## Suggested next steps

If you want to expand this project further, a good next step would be to add:

- a training job for a real model
- a model serving endpoint
- automated CI/CD for deployment
- dashboards for monitoring and observability
- a more production-like deployment using a managed cloud provider

## Summary

This project is not just a crypto demo. It is a reusable reference implementation for building an ephemeral, modern ML platform that can be created in minutes and destroyed just as easily.

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

kubectl run kafka-consumer -n infra -it --rm \
  --image=quay.io/strimzi/kafka:0.46.0-kafka-4.0.0 --restart=Never -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server my-cluster-kafka-bootstrap:9092 \
  --topic crypto-prices \
  --from-beginning


That’s why your SSH tunnel (9094) from your laptop → EC2 made it work:
  Laptop connects to localhost:9094
  Tunnel forwards to EC2:9094
  EC2 forwards via NodePort to the Kafka broker pod.


# optional Time being we can check on
python websocket_kafka_consumer.py 
The pod will attach to your cluster Kafka.
You’ll see all messages your Python producer sent.
Good for testing / debugging before moving to your MinIO consumer.

