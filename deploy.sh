#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

git pull

# --provenance=false --sbom=false avoids a BuildKit gotcha: without them,
# attestation metadata turns the image into a multi-manifest index that
# doesn't cleanly retag on a repeat `ctr images import` of the same tag.
docker build --provenance=false --sbom=false -t athenaeum:latest .
docker save athenaeum:latest -o athenaeum.tar

# Explicitly removing the old image first guards against that same stale-
# digest issue if one ever slips through anyway. The sync CronJob shares
# this same image/tag, so it picks up the update on its next scheduled run
# with no separate step needed.
sudo k3s ctr images rm docker.io/library/athenaeum:latest || true
sudo k3s ctr images import athenaeum.tar
rm -f athenaeum.tar

kubectl rollout restart deployment athenaeum-api
kubectl rollout status deployment athenaeum-api
