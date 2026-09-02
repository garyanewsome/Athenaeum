"""Real vault sync: pull the private GitHub repo, diff against the
last-seen commit (the persistent clone's own git history *is* that
state — no separate tracking file needed), and only re-embed files
that actually changed. Deleted files get their stale chunks removed.

Meant to run on a schedule (K8s CronJob) against a persistent clone
directory (VAULT_REPO_PATH, backed by a PersistentVolume in-cluster).
First run clones fresh and ingests everything; every run after that
is incremental.
"""

import subprocess
from pathlib import Path

from app.chunking import chunk_markdown
from app.config import VAULT_REPO_PATH, VAULT_REPO_URL
from app.embeddings import embed
from app.store import add_chunks, delete_by_source


def run_git(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def sync_file(repo_root: Path, relative_path: str) -> None:
    """Re-embed one file from scratch (delete-then-readd avoids stale
    leftover chunks if a file shrinks or its structure changes)."""
    delete_by_source(relative_path)

    full_path = repo_root / relative_path
    if not full_path.exists():
        print(f"Removed: {relative_path}")
        return

    text = full_path.read_text(encoding="utf-8")
    chunks = chunk_markdown(text)
    if not chunks:
        return

    ids = [f"{relative_path}:{i}" for i in range(len(chunks))]
    embeddings = [embed(chunk) for chunk in chunks]
    metadatas = [{"source": relative_path} for _ in chunks]

    add_chunks(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
    print(f"Re-ingested {len(chunks)} chunk(s) from {relative_path}")


def main() -> None:
    repo_path = Path(VAULT_REPO_PATH)

    if not repo_path.exists():
        print(f"No existing clone — cloning {VAULT_REPO_URL} into {repo_path}")
        run_git("clone", VAULT_REPO_URL, str(repo_path))
        md_files = sorted(p.relative_to(repo_path).as_posix() for p in repo_path.rglob("*.md"))
        for relative_path in md_files:
            sync_file(repo_path, relative_path)
        return

    old_head = run_git("rev-parse", "HEAD", cwd=repo_path)
    run_git("pull", "--ff-only", cwd=repo_path)
    new_head = run_git("rev-parse", "HEAD", cwd=repo_path)

    if old_head == new_head:
        print("No changes since last sync.")
        return

    changed = run_git("diff", "--name-only", old_head, new_head, cwd=repo_path)
    changed_files = [line for line in changed.splitlines() if line.endswith(".md")]

    if not changed_files:
        print(f"{old_head[:7]}..{new_head[:7]}: no markdown changes.")
        return

    print(f"{old_head[:7]}..{new_head[:7]}: {len(changed_files)} changed markdown file(s)")
    for relative_path in changed_files:
        sync_file(repo_path, relative_path)


if __name__ == "__main__":
    main()
