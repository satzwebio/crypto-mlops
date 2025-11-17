import os
import json
import signal
import sys
import time
from datetime import datetime, timezone
from io import BytesIO
from confluent_kafka import Consumer, TopicPartition

import boto3
import pandas as pd
from confluent_kafka import Consumer, KafkaException, KafkaError

RUNNING = True


def handle_signals(signum, frame):
    global RUNNING
    print(f"Received signal {signum}, shutting down gracefully...")
    RUNNING = False


signal.signal(signal.SIGINT, handle_signals)
signal.signal(signal.SIGTERM, handle_signals)


def create_kafka_consumer():
    config = {
        "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS"),
        "group.id": os.getenv("KAFKA_CONSUMER_GROUP"),
        "auto.offset.reset": os.getenv("KAFKA_AUTO_OFFSET_RESET", "earliest"),
        "enable.auto.commit": False,
    }

    consumer = Consumer(config)

    topic = os.getenv("KAFKA_TOPIC", "crypto-prices")
    partition = int(os.getenv("KAFKA_PARTITION", "0"))

    tp = TopicPartition(topic, partition, 0)

    consumer.assign([tp])

    print(f"🔥 Assigned to {topic} partition {partition}")

    return consumer


def create_s3_client():
    endpoint_url = os.getenv("MINIO_ENDPOINT", "http://minio.infra.svc.cluster.local:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY")
    secret_key = os.getenv("MINIO_SECRET_KEY")
    region = os.getenv("MINIO_REGION", "us-east-1")

    session = boto3.session.Session()
    s3 = session.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )
    print(f"Created S3 client for endpoint {endpoint_url}")
    return s3


# ---------------------------------------------------------
# UPDATED parse_message() — guaranteed printing, correct parsing
# ---------------------------------------------------------
def parse_message(msg):
    try:
        raw = msg.value()
        print("🔥 RAW:", raw)

        if raw is None:
            print("❌ msg.value() is None")
            return None

        # Ensure raw is bytes
        if isinstance(raw, bytes):
            payload = raw.decode("utf-8", errors="replace")
        else:
            print("❌ RAW IS NOT BYTES:", type(raw))
            return None

        print("📄 STRING PAYLOAD:", payload)

        # Try JSON decode
        try:
            data = json.loads(payload)
        except Exception as je:
            print("❌ JSON LOAD FAILED:", je)
            return None

        print("📦 JSON PARSED:", data)

        symbol = data.get("symbol")
        price = data.get("price")
        event_ts_ms = data.get("timestamp")

        if event_ts_ms:
            event_timestamp = datetime.utcfromtimestamp(event_ts_ms / 1000)
        else:
            event_timestamp = datetime.utcnow()

        parsed = {
            "event_timestamp": event_timestamp,
            "symbol": symbol,
            "price": price,
            "volume": None,
            "source": "binance",
            "ingest_ts": datetime.utcnow()
        }

        print("✅ FINAL PARSED:", parsed)
        return parsed

    except Exception as e:
        print("🔥 UNEXPECTED ERROR IN parse_message:", e)
        return None


def buffer_to_parquet_s3(s3_client, records, batch_start_ts):
    bucket = os.getenv("MINIO_BUCKET", "feast-feature-store")

    dt = datetime.fromtimestamp(batch_start_ts, tz=timezone.utc)
    date_str = dt.strftime("%Y%m%d")
    time_str = dt.strftime("%H%M%S")

    key_prefix = os.getenv("MINIO_PREFIX", "raw")
    filename = f"crypto_prices_{date_str}_{time_str}.parquet"
    key = f"{key_prefix}/{date_str}/{filename}"

    print(f"\n📝 Writing batch of {len(records)} records to s3://{bucket}/{key}")

    df = pd.DataFrame(records)

    buffer = BytesIO()
    df.to_parquet(buffer, index=False)
    buffer.seek(0)

    s3_client.put_object(Bucket=bucket, Key=key, Body=buffer)
    print(f"✅ Successfully uploaded parquet to s3://{bucket}/{key}")


def main():
    consumer = create_kafka_consumer()
    s3_client = create_s3_client()

    batch_max_seconds = int(os.getenv("BATCH_MAX_SECONDS", "60"))
    batch_max_messages = int(os.getenv("BATCH_MAX_MESSAGES", "5000"))
    poll_timeout = float(os.getenv("KAFKA_POLL_TIMEOUT", "1.0"))

    records = []
    batch_start_ts = time.time()

    try:
        while RUNNING:
            msg = consumer.poll(timeout=poll_timeout)

            now = time.time()

            if msg is None:
                print("NO MESSAGE FROM KAFKA")
                if records and (now - batch_start_ts >= batch_max_seconds):
                    try:
                        buffer_to_parquet_s3(s3_client, records, batch_start_ts)
                        consumer.commit(asynchronous=False)
                        print("🔄 Offsets committed.")
                    except Exception as e:
                        print(f"❌ Error writing batch to MinIO: {e}")
                    finally:
                        records = []
                        batch_start_ts = now
                continue

            if msg.error():
                print("🔥 RECEIVED RAW:", msg.value())
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    raise KafkaException(msg.error())

            # PRINT EVERY MESSAGE
            print("\n------------------------------------------")
            print("📌 NEW MESSAGE RECEIVED:")
            print("------------------------------------------")

            parsed = parse_message(msg)

            if parsed is not None:
                records.append(parsed)

            if len(records) == 1:
                batch_start_ts = now

            if len(records) >= batch_max_messages or (now - batch_start_ts >= batch_max_seconds):
                try:
                    buffer_to_parquet_s3(s3_client, records, batch_start_ts)
                    consumer.commit(asynchronous=False)
                    print("🔄 Offsets committed.")
                except Exception as e:
                    print(f"❌ Error writing batch to MinIO: {e}")
                finally:
                    records = []
                    batch_start_ts = now

    except Exception as e:
        print(f"💥 Fatal error in consumer: {e}")
    finally:
        if records:
            try:
                print("🧹 Flushing remaining records...")
                buffer_to_parquet_s3(s3_client, records, batch_start_ts)
                consumer.commit(asynchronous=False)
            except Exception as e:
                print(f"❌ Error flushing final batch: {e}")
        consumer.close()
        print("👋 Kafka consumer closed.")


if __name__ == "__main__":
    main()
