# Athenaeum

RAG retrieval API over a unified Obsidian vault. Formerly planned under
the working title "VaultMind" — renamed to avoid clashing with an
earlier unrelated project of that name.

General-purpose, not tied to any one persona or chat app — consumers
(starting with Hermes) call this API, not the other way around.

Deployed as its own thing in the [homelab](../homelab) K3s cluster —
own Deployment, Service, and Ingress hostname (`athenaeum.home.local`,
tentative). See the homelab README's Phase 5 for how this fits into
the larger build.

## What it does

Given a query, return relevant chunks from the Obsidian vault plus
their source note paths. That's it — no chat logic, no persona, no
conversation state. Consumers (chat apps) call this as a tool during
their own conversations and inject the results into their own model's
context.

## Planned pipeline

1. Obsidian vault lives in a **private GitHub repo**
2. A **K8s CronJob** periodically pulls the repo, diffs against the
   last-seen commit (avoid re-embedding everything every run)
3. Chunk + embed changed content into a vector store (**Chroma or
   Qdrant** — not yet decided)
4. Expose a retrieval endpoint, e.g. `POST /search {"query": "..."}`
   → matched chunks + source paths

Security posture: private repo + SSH-keyed access from the homelab is
considered reasonable; the realistic exposure is GitHub-account
compromise, not the homelab itself.

## Status — scaffolded, working locally

- **Stack decided:** Python + FastAPI, **Chroma running embedded**
  (in-process, persisted to `./chroma_data`) rather than a separate
  Qdrant service — no extra Deployment/PVC needed until this actually
  needs to scale past a single vault.
- **Embedding model:** `nomic-embed-text`, served by the homelab's
  Ollama over the LAN (`OLLAMA_HOST` env var, defaults to
  `http://192.168.1.157:11434`).
- **Chunking:** header-aware — splits on markdown headers first, falls
  back to paragraph-based splitting for any section over ~1500 chars.
  Simple, not yet tuned; revisit if retrieval quality suffers on real
  notes.
- **Tested locally:** ingested `sample_vault/` (2 throwaway notes, not
  the real Obsidian vault) via `python ingest.py ./sample_vault`, ran
  the API with `uvicorn app.main:app`, queried `/search` — top result
  correctly matched the relevant note by a wide margin over irrelevant
  ones. Confirms the embed → store → retrieve pipeline works end to
  end.

### Still open
- No debug/query UI — not needed, direct API calls are the intended
  usage (consumed as a tool by other apps, not by a human)
- Chunking quality unrefined — a loosely-related query returned only
  weak matches (large distances) during testing. Mechanism is correct,
  retrieval *quality* just hasn't been tuned yet. Revisit if/when a
  real consumer app makes this matter.

### `/browse` — structural folder listing, built + image ready, not yet live
Added after a real Hermes conversation surfaced a genuine gap: asked
for files in a specific folder ("Burn St Productions"), got back
results from three unrelated folders — semantic search has no concept
of "list files under this exact path," it can only return "content
that sounds related." `/browse {"folder": "..."}` (`app/browse.py`) is
a literal directory listing against the same repo clone `sync.py`
already maintains — case-insensitive substring match on folder name,
returns matched folders + their `.md` files, or falls back to listing
top-level folders if nothing matches. No path-traversal risk: `folder`
is only ever matched against directory names already discovered via
`rglob()`, never joined directly into a path.

**Real bug caught and fixed while building this:** `athenaeum-api.yaml`
never set `VAULT_REPO_PATH`, so the API pod was defaulting to
`./vault-repo` (inside `/app`) instead of `/data/vault-repo` where the
CronJob actually clones it — the API could never have seen the synced
repo for *any* future file-level feature, not just this one. Fixed and
**already applied live** (just an env var, no new image needed).

**Deployment status:** image built (includes `/browse`) and sitting as
a tarball on the server (`/tmp/athenaeum.tar`), but not yet imported —
that needs the one `sudo k3s ctr images import` step. Once imported,
restart with `kubectl rollout restart deployment/athenaeum-api`. Not
yet tested against the real vault (only logic-tested locally against
a `sample_vault` fixture) — verify with the actual failing query once
deployed: ask Hermes to list files in "Burn St Productions."

### API deployed — live on the LAN
`k8s/athenaeum-api.yaml` — Deployment + Service + Ingress
(`athenaeum.home.local`), same PVC as the CronJob so it reads the same
data the sync job writes. Verified through the real Traefik Ingress
path (not localhost) with both `/health` and a real `/search` query
against actual vault content.

Both the CronJob and the API now exist as living K3s resources — this
phase (Phase 5 in the homelab README) is functionally complete for a
v1: real vault, real hourly sync, real queryable API.

### CronJob — live, real vault fully ingested
`k8s/vault-sync-cronjob.yaml` applied and working against the real
`garyanewsome/obsidian-vault` repo (not a fixture) — runs hourly,
PVC-backed (`athenaeum-data`, `/mnt/storage/athenaeum-data`) so the
clone and Chroma data survive between runs.

First real run: all 281 markdown files ingested in ~63 seconds.
Verified with an actual query against the real data (not a synthetic
test) — asked about house tasks/furniture, got back the correct daily
notes discussing the task-tracking system. Full pipeline confirmed
end to end on real content, not just the fixture/sample tests.

Image build note: this session's `docker build`/`kubectl` commands
ran without `sudo` (user added to the `docker` group, kubeconfig
copied to `~/.kube/config` with user ownership) — this was set up
specifically so Claude Code could operate on the homelab directly over
SSH instead of relaying every command through the user. `k3s ctr
images import` still needs `sudo` (containerd socket is root-only) —
deliberately left as a manual step each rebuild rather than granting
broader passwordless sudo.

### `sync.py` — real diff-aware sync, tested working
Keeps a persistent clone (`VAULT_REPO_PATH`); the clone's own git
history *is* the "last-seen commit" state, no separate tracking file
needed. Each run: `git pull`, diff old HEAD vs. new HEAD, and for each
changed `.md` file, delete its existing chunks and re-embed the
current version (handles edits and deletions correctly, no orphaned
stale chunks). First run (no existing clone) ingests everything.

Verified against a local git fixture (not the real vault, to avoid an
unnecessary full 281-file embed run just to test logic — same code
path either way since `git clone` works against local paths too):
- Fresh clone → ingested both files
- Re-run, no changes → correctly no-ops
- Edited one file + added another → re-ingested exactly those two,
  left the untouched file alone
- Deleted a file → its chunks removed, confirmed via direct store
  inspection (no stale/duplicate chunks left over)

### CronJob + Secret mechanism — confirmed working
Smoke-tested with a throwaway CronJob (`alpine/git`, K8s Secret
holding the deploy key, plain `git clone`, no real logic) before
building anything real on top — same pattern as the `whoami` Ingress
test in the homelab repo. Result: 281 markdown files cloned
successfully from inside a K3s pod. Confirms Secrets, container
networking, and GitHub SSH access all work from inside the cluster,
not just from the bare server. Torn down after confirming (`kubectl
delete cronjob/job/secret`) — will get rebuilt for real once the sync
script exists.

### Vault repo access — confirmed working
Dedicated deploy key (read-only, not the personal GitHub SSH key) on
the homelab server: `~/.ssh/id_ed25519_vault`, added as a Deploy Key
on `garyanewsome/obsidian-vault` (write access left unchecked). Test
clone via `GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519_vault" git clone
git@github.com:garyanewsome/obsidian-vault.git` succeeded.

### Running it locally
```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python ingest.py ./sample_vault
.venv/bin/uvicorn app.main:app --reload
# then: curl -X POST localhost:8000/search -d '{"query": "..."}'
```
Needs Python 3.12 — 3.14 currently fails to build a chromadb
dependency (no wheels yet for that new a release).
