5️⃣ Validation Checklist

Once deployed:

Check pod status

kubectl get pods -n crypto -l app=crypto-kafka-consumer
kubectl logs -n crypto deploy/crypto-kafka-consumer -f


You should see logs like:

“Subscribed to topic: crypto-prices”

“Writing batch of X records to s3://feast-feature-store/raw/20251115/crypto_prices_20251115_120000.parquet”

“Committed offsets after successful batch write.”

Verify files in MinIO

Use mc or the MinIO UI:

mc ls local/feast-feature-store/raw/
mc ls local/feast-feature-store/raw/20251115/


You should see your Parquet files.

Sanity check content

Download one Parquet and open locally / in a notebook:

import pandas as pd
df = pd.read_parquet("crypto_prices_20251115_120000.parquet")
print(df.head())
