#!/usr/bin/env bash
set -e

echo "📦 Running feast apply..."
feast apply

END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%S")
echo "⏱  Materializing incremental features up to: $END_TIME"

feast materialize-incremental $END_TIME
echo "✅ Materialization completed."
