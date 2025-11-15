FROM python:3.10-slim
WORKDIR /app
COPY websocket_kafka_producer.py requirements.txt ./
RUN pip install -r requirements.txt
CMD ["python", "websocket_kafka_producer.py"]
