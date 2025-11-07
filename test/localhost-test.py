import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="mlopsdb",
    user="mlops",
    password="your_password",
    port=5432
)
print("✅ Connected successfully!")
conn.close()


import redis

try:
    # Adjust host and port as needed
    client = redis.Redis(host='localhost', port=6379, decode_responses=True)

    # Try a simple ping command
    response = client.ping()
    if response:
        print("✅ Successfully connected to Redis on localhost:6379")
    else:
        print("⚠️ Connected, but ping returned unexpected response:", response)

except redis.exceptions.ConnectionError as e:
    print("❌ Could not connect to Redis:", e)
except Exception as e:
    print("⚠️ An unexpected error occurred:", e)

