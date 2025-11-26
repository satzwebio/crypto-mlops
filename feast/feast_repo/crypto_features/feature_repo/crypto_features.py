from feast import FileSource, Entity, Field, FeatureView
from feast.types import Float64
from feast.data_format import ParquetFormat

crypto_source = FileSource(
    name="crypto_source",
    path="s3://feast-feature-store/raw/",
    timestamp_field="event_timestamp",
    file_format=ParquetFormat(),
    s3_endpoint_override="http://minio-service.infra.svc.cluster.local:9000",
)

crypto_entity = Entity(name="symbol", join_keys=["symbol"])

crypto_fv = FeatureView(
    name="crypto_prices",
    entities=[crypto_entity],
    ttl=None,
    schema=[
        Field(name="price", dtype=Float64),
        Field(name="volume", dtype=Float64),
    ],
    source=crypto_source,
    online=True,
)
