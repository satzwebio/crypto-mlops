import mlflow, tempfile, os

mlflow.set_experiment("local-test")

with mlflow.start_run():
    mlflow.log_param("lr", 0.05)
    mlflow.log_metric("accuracy", 0.93)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("Test artifact from local MLflow client")
        temp_path = f.name
    mlflow.log_artifact(temp_path)
    print("✅ Logged successfully to MLflow + MinIO")