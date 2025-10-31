import pandas as pd
from sqlalchemy import create_engine

# Configuration
db_user = "mlops"
db_password = "mlops123"
db_host = "localhost"
db_port = 5432
db_name = "feast_offline"
table_name = "crypto_proces"
parquet_file = "feast_repo/crypto_features/feature_repo/data/crypto_prices.parquet"  # Adjust the path if needed


# Create SQLAlchemy engine
engine = create_engine(f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}")

# Read the parquet file
df = pd.read_parquet(parquet_file)

# Optional: check the first few rows
print(df.head())

# Load data into Postgres
df.to_sql(table_name, engine, if_exists='replace', index=False)

print(f"Data from {parquet_file} loaded into {table_name} successfully!")
