from confluent_kafka import Consumer

conf = {
    'bootstrap.servers': 'localhost:9094',
    'group.id': 'crypto-consumer',
    'auto.offset.reset': 'earliest'
}

consumer = Consumer(conf)
consumer.subscribe(['crypto-prices'])

print("✅ Listening for Kafka messages...\n")
try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print(f"⚠️ Error: {msg.error()}")
            continue
        print(f"💬 Received: {msg.value().decode('utf-8')}")
except KeyboardInterrupt:
    pass
finally:
    consumer.close()
