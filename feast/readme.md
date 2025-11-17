docker build -t satzweb/feast-runner:latest -f Dockerfile .
docker push satzweb/feast-runner:latest


kubectl -n crypto get pods --field-selector=status.phase=Failed -o name | xargs kubectl -n crypto delete
