# Athenaeum

RAG retrieval and structural folder-listing API over a personal Obsidian vault.

## What it does

- `POST /search {"query": "...", "top_k": 5}` — semantic search, returns matching chunks with source paths and distance scores
- `POST /browse {"folder": "..."}` — literal folder listing (case-insensitive substring match on folder name), returns matched folders + their `.md` files, or top-level folders if nothing matches
- `GET /health`

No chat logic, no persona, no conversation state — a pure retrieval service meant to be called by other applications as a tool.

## Sync pipeline

A K8s CronJob (`k8s/vault-sync-cronjob.yaml`, hourly) runs `sync.py`:

1. Pulls the vault's private GitHub repo via a read-only deploy key
2. Diffs against the last-seen commit (the clone's own git history is the tracking state — no separate file needed)
3. For each changed `.md` file: deletes its existing chunks and re-embeds the current version (handles edits and deletions correctly, no orphaned chunks)
4. First run (no existing clone) ingests everything

## Stack

- Python + FastAPI
- Chroma, embedded (in-process, persisted to disk/PVC) — not a separate service
- Embeddings via Ollama (`nomic-embed-text`)
- Chunking: header-aware markdown splitting, paragraph fallback for sections over ~1500 chars

## Running it locally

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python ingest.py ./sample_vault
.venv/bin/uvicorn app.main:app --reload
# then: curl -X POST localhost:8000/search -d '{"query": "..."}'
```

Needs Python 3.12 — 3.14 currently fails to build a chromadb dependency (no wheels published yet for that new a release).

## Deployment

Runs in K3s:
- `k8s/athenaeum-api.yaml` — Deployment + Service + Ingress (`athenaeum.home.local`)
- `k8s/athenaeum-pv.yaml` — PersistentVolume/Claim, shared between the API and the sync CronJob
- `k8s/vault-sync-cronjob.yaml` — the hourly sync job

No container registry — images are built locally and loaded directly via `k3s ctr images import` (see the homelab repo for the general K3s setup).

To redeploy after a code change: `./deploy.sh` — builds the image, reimports it into K3s, and restarts the deployment. The sync CronJob shares the same image, so it picks up the change on its next scheduled run automatically.

## Status

- [x] `/search` — working against the real vault
- [x] `/browse` — working against the real vault
- [x] Hourly sync CronJob — live
- [ ] Chunking quality — functional, not tuned; revisit if a consumer app's retrieval quality suffers
- [ ] No debug/query UI — not needed, this is API-only by design
