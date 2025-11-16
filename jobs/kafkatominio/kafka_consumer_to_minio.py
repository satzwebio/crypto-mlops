import os
import json
import signal
import sys
import time
from datetime import datetime, timezone
from io import BytesIO

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
        "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
        "group.id": os.getenv("KAFKA_CONSUMER_GROUP", "crypto-minio-consumer"),
        "auto.offset.reset": os.getenv("KAFKA_AUTO_OFFSET_RESET", "earliest"),
        "enable.auto.commit": False,
    }
    consumer = Consumer(config)
    topic = os.getenv("KAFKA_TOPIC", "crypto-prices")
    consumer.subscribe([topic])
    print(f"Subscribed to topic: {topic}")
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


def parse_message(msg):
    """
    Converts Binance-style Kafka payload into Feast-friendly flat schema.
    """

    try:
        payload = msg.value().decode("utf-8")
        data = json.loads(payload)

        # Kafka metadata
        kafka_ts = msg.timestamp()[1]  # milliseconds

        # Binance fields (adjust if your producer differs)
        symbol = data.get("s")
        price = float(data.get("p")) if data.get("p") else None
        volume = float(data.get("q")) if data.get("q") else None

        # Binance event timestamp (ms → datetime)
        evt_ts_ms = data.get("E")  
        if evt_ts_ms:
            event_ts = datetime.utcfromtimestamp(evt_ts_ms / 1000.0)
        else:
            # fallback to kafka timestamp
            event_ts = datetime.utcfromtimestamp(kafka_ts / 1000.0)

        # Final feast-friendly dict
        return {
            "event_timestamp": event_ts,
            "symbol": symbol,
            "price": price,
            "volume": volume,
            "source": "binance",
            "ingest_ts": datetime.utcfromtimestamp(kafka_ts / 1000.0)
        }

    except Exception as e:
        print(f"Failed to parse message: {e}\nPayload={msg.value()}")
        return None



def buffer_to_parquet_s3(s3_client, records, batch_start_ts):
    bucket = os.getenv("MINIO_BUCKET", "feast-feature-store")

    # Use UTC timestamp of batch start to build path
    dt = datetime.fromtimestamp(batch_start_ts, tz=timezone.utc)
    date_str = dt.strftime("%Y%m%d")
    time_str = dt.strftime("%H%M%S")

    # Path: raw/YYYYMMDD/crypto_prices_YYYYMMDD_HHMMSS.parquet
    key_prefix = os.getenv("MINIO_PREFIX", "raw")
    filename = f"crypto_prices_{date_str}_{time_str}.parquet"
    key = f"{key_prefix}/{date_str}/{filename}"

    print(f"Writing batch of {len(records)} records to s3://{bucket}/{key}")

    df = pd.DataFrame(records)

    # If 'raw_payload' is nested, you can normalize:
    # df = pd.json_normalize(records, sep="_")

    buffer = BytesIO()
    df.to_parquet(buffer, index=False)
    buffer.seek(0)

    s3_client.put_object(Bucket=bucket, Key=key, Body=buffer)
    print(f"Successfully uploaded parquet to s3://{bucket}/{key}")


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
                # No message, check if we should flush due to time
                if records and (now - batch_start_ts >= batch_max_seconds):
                    try:
                        buffer_to_parquet_s3(s3_client, records, batch_start_ts)
                        consumer.commit(asynchronous=False)
                        print("Committed offsets after successful batch write.")
                    except Exception as e:
                        print(f"Error writing batch to MinIO: {e}")
                        # Do NOT commit offsets on failure
                    finally:
                        records = []
                        batch_start_ts = now
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition event
                    continue
                else:
                    raise KafkaException(msg.error())

            parsed = parse_message(msg)
            if parsed is not None:
                records.append(parsed)

            # On first record in a fresh batch, reset start time
            if len(records) == 1:
                batch_start_ts = now

            # Check batch size / time thresholds
            if len(records) >= batch_max_messages or (now - batch_start_ts >= batch_max_seconds):
                try:
                    buffer_to_parquet_s3(s3_client, records, batch_start_ts)
                    consumer.commit(asynchronous=False)
                    print("Committed offsets after successful batch write.")
                except Exception as e:
                    print(f"Error writing batch to MinIO: {e}")
                    # Do NOT commit offsets on failure
                finally:
                    records = []
                    batch_start_ts = now

    except Exception as e:
        print(f"Fatal error in consumer loop: {e}")
    finally:
        # Flush remaining records on shutdown
        if records:
            try:
                print("Flushing remaining records before shutdown...")
                buffer_to_parquet_s3(s3_client, records, batch_start_ts)
                consumer.commit(asynchronous=False)
            except Exception as e:
                print(f"Error flushing final batch: {e}")
        consumer.close()
        print("Kafka consumer closed.")


if __name__ == "__main__":
    main()
