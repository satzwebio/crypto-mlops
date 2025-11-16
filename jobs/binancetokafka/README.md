# WebSocket → Kafka Producer Deployment

This service streams live crypto prices from Binance WebSocket to Kafka topic `crypto-prices`.

---

## 1️⃣ Build Docker Image

```bash
Create repo first in docker hub

docker build -t satzweb/websocket-producer:latest .
docker push satzweb/websocket-producer:latest
```

2️⃣ Deploy to Kubernetes

Update the image: field in kafka-producer.yaml to your image name, then:
kubectl apply -f kafka-producer.yaml -n infra

Check the logs:
```bash
kubectl logs -f deploy/kafka-producer -n infra
```

You should see:
✅ Connected to Binance WebSocket...
📈 Sent: {'symbol': 'BTCUSDT', 'price': 102452.39, 'timestamp': ...}
✅ Message delivered to crypto-prices [0]


3️⃣ Verify in Kafka
Consume messages using the Strimzi CLI container:
```bash
kubectl run kafka-consumer -n infra -it --rm \
  --image=strimzi/kafka:0.46.0-kafka-4.0.0 --restart=Never -- \
  kafka-console-consumer.sh \
  --bootstrap-server my-cluster-kafka-bootstrap:9092 \
  --topic crypto-prices \
  --from-beginning
  ```


🔄 Notes

This Deployment runs continuously and restarts automatically if it crashes.
For multiple symbols, you can scale replicas or create separate Deployments.
Environment variables like TOPIC and KAFKA_BROKER can be updated in the YAML file.

---

