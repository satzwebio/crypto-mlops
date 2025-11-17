from feast import FeatureStore

# Initialize store (path where your feature_store.yaml is)
store = FeatureStore(repo_path=".")

# Fetch features for a specific symbol (example: BTCUSDT)
feature_vector = store.get_online_features(
    features=[
        "crypto_features:price",
        "crypto_features:volume",
    ],
    entity_rows=[{"symbol": "BTCUSDT"}],
).to_dict()

print(feature_vector)