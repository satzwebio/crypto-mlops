docker build -t satzweb/feast-runner:latest3 -f Dockerfile .
docker push satzweb/feast-runner:latest3


kubectl -n crypto get pods --field-selector=status.phase=Failed -o name | xargs kubectl -n crypto delete


kubectl apply -f feast/manifest/feast-materialize-cronjob.yaml