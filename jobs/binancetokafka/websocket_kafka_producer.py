import asyncio
import json
import websockets
import os
from confluent_kafka import Producer

# ✅ 1. Kafka Configuration
# Use localhost since you're port-forwarding from your local machine
KAFKA_BROKER = os.getenv("KAFKA_BROKER")   # "localhost:9094"
TOPIC = os.getenv("TOPIC")
# commented out for now, since deployment has env vars set

# ✅ 2. Binance WebSocket Endpoint
BINANCE_STREAM = "wss://stream.binance.us:9443/ws/btcusdt@trade"

# ✅ 3. Kafka Producer Setup
producer_conf = {
    "bootstrap.servers": KAFKA_BROKER,
    "client.id": "crypto-price-producer"
}
producer = Producer(producer_conf)


# ✅ 4. Delivery Callback (Optional, for debugging)
def delivery_report(err, msg):
    if err is not None:
        print(f"❌ Delivery failed: {err}")
    else:
        print(f"✅ Message delivered to {msg.topic()} [{msg.partition()}]")


# ✅ 5. Stream Prices from Binance WebSocket
async def stream_prices():
    uri = BINANCE_STREAM
    print("✅ Connected to Binance WebSocket...")

    async with websockets.connect(uri) as websocket:
        while True:
            msg = await websocket.recv()
            data = json.loads(msg)

            # Extract and format the message
            payload = {
                "symbol": data.get("s"),
                "price": float(data.get("p")),
                "timestamp": data.get("T")
            }

            # Send to Kafka topic
            producer.produce(
                topic=TOPIC,
                key=payload["symbol"],
                value=json.dumps(payload),
                callback=delivery_report
            )

            producer.poll(0)
            print(f"📈 Sent: {payload}")


# ✅ 6. Run Event Loop
if __name__ == "__main__":
    try:
        asyncio.run(stream_prices())
    except KeyboardInterrupt:
        print("🛑 Interrupted by user.")
    finally:
        producer.flush()
