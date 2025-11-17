from datetime import timedelta
from feast import Entity, FeatureView, Field, FileSource
from feast.types import Float32, ValueType
from feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source import PostgreSQLSource

# 1. Entity definition
crypto_entity = Entity(
    name="symbol",
    value_type=ValueType.STRING,   # ✅ Enum, required
    description="Cryptocurrency trading symbol"
)

# 2. Data source
# file_source = FileSource(
#     path="data/crypto_prices.parquet",
#     timestamp_field="event_timestamp",
#     created_timestamp_column="created",
# )

crypto_source = PostgreSQLSource(
    name="crypto_source",
    query="SELECT * FROM crypto_proces",
    timestamp_field="event_timestamp",
    created_timestamp_column="created",
)



# 3. Feature view
crypto_features = FeatureView(
    name="crypto_features",
    entities=[crypto_entity],   # ✅ MUST be list of Entity objects
    ttl=timedelta(days=7),
    schema=[
        Field(name="price", dtype=Float32),
        Field(name="volume", dtype=Float32),
        Field(name="price_ma_5", dtype=Float32),
        Field(name="price_ma_10", dtype=Float32),
        Field(name="price_volatility", dtype=Float32),
    ],
    online=True,
    # source=file_source,
    source=crypto_source,
)
