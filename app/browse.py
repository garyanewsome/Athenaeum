"""Structural folder listing — complements /search (semantic) with a
literal directory lookup against the same repo clone sync.py maintains.
RAG can answer "what do my notes say about X" but has no concept of
"what files exist under folder X" — that needs a real listing, not a
similarity search. No path-traversal risk: `folder_name` is only ever
used as a case-insensitive substring match against directory names
already discovered via rglob() under the repo root, never joined
directly into a filesystem path."""

from pathlib import Path

from app.config import VAULT_REPO_PATH


def list_notes(folder_name: str) -> dict:
    repo_root = Path(VAULT_REPO_PATH).resolve()
    if not repo_root.exists():
        return {"error": "Vault not yet synced — no repo clone present."}

    needle = folder_name.lower()
    matching_dirs = sorted(
        (d for d in repo_root.rglob("*") if d.is_dir() and needle in d.name.lower()),
        key=lambda d: d.relative_to(repo_root).as_posix(),
    )

    if not matching_dirs:
        top_level = sorted(
            d.name for d in repo_root.iterdir() if d.is_dir() and not d.name.startswith(".")
        )
        return {"matched_folders": [], "top_level_folders": top_level}

    results = []
    for d in matching_dirs:
        files = sorted(p.relative_to(repo_root).as_posix() for p in d.rglob("*.md"))
        results.append({"folder": d.relative_to(repo_root).as_posix(), "files": files})

    return {"matched_folders": results}
