#!/bin/bash
set -xe
docker compose build && docker compose push
kubectl apply -k deployments/k8s
kubectl -n testmcp rollout restart deployment testmcp
