"""Open-checkbox scan of the vault clone (`- [ ] text`), for Hermes's
nightly Obsidian -> Todo import. Reads the same clone sync.py maintains, so
it only sees what's been pushed to the vault's git remote. Limited to
TASKS_SCAN_FOLDER (daily notes) — not song/project notes.

Two kinds of noise found in the real vault, both filtered here rather than
left for the caller to guess at:
- empty checkboxes (`- [ ]` with no text) — daily-note template scaffolding
- the same text repeated across many notes ("Write one line everyday" is in
  ~19 daily notes, "Music Production" in ~10) — a habit/template line, not
  a task. Anything appearing in REPEAT_THRESHOLD or more distinct files is
  treated as that and dropped, without hardcoding any particular text.
A task carried forward through a few consecutive daily notes stays under
the threshold and comes back once, not once per note.
"""

import re
from pathlib import Path

from app.config import TASKS_SCAN_FOLDER, VAULT_REPO_PATH

REPEAT_THRESHOLD = 5

# Tolerates `-[ ]` (no space) as well as the standard `- [ ]`, and `*` bullets.
_OPEN_TASK = re.compile(r"^\s*[-*]\s*\[ \]\s*(\S.*?)\s*$")
_DUE = re.compile(r"\s*📅\s*(\d{4}-\d{2}-\d{2})")


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _skipped(relative: Path) -> bool:
    return any(part.startswith(".") or part.lower() == "templates" for part in relative.parts)


def _resolve_extra(repo_root: Path, relative: str) -> Path | None:
    path = (repo_root / relative).resolve()
    if repo_root in path.parents and path.is_file() and path.suffix == ".md":
        return path
    return None


def scan_open_tasks(extra_files: list[str] | None = None) -> dict:
    """extra_files: additional vault-relative .md files to scan beyond
    TASKS_SCAN_FOLDER — used by Hermes's one-time first-run import of a
    standing task-list note. A path that doesn't resolve to a real .md file
    inside the vault is an error, not silently skipped, so a caller relying
    on it (and about to record "done") finds out."""
    repo_root = Path(VAULT_REPO_PATH).resolve()
    if not repo_root.exists():
        return {"error": "Vault not yet synced — no repo clone present."}

    scan_root = (repo_root / TASKS_SCAN_FOLDER).resolve()
    if not scan_root.is_dir() or repo_root not in scan_root.parents:
        return {"error": f"Task scan folder not found in the vault: {TASKS_SCAN_FOLDER}"}

    paths = sorted(scan_root.rglob("*.md"))
    for relative in extra_files or []:
        extra = _resolve_extra(repo_root, relative)
        if extra is None:
            return {"error": f"Extra file not found in the vault: {relative}"}
        if extra not in paths:
            paths.append(extra)

    # normalized text -> {"text", "due", "sources": [relative paths]}
    found: dict[str, dict] = {}
    for path in paths:
        relative = path.relative_to(repo_root)
        if _skipped(relative):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line in lines:
            match = _OPEN_TASK.match(line)
            if not match:
                continue
            raw = match.group(1)
            # The Tasks plugin's own recurrence (e.g. birthdays: "🔁 every
            # year") — the plugin already owns re-surfacing those inside
            # Obsidian, and importing one as a plain one-off todo would
            # misrepresent it.
            if "🔁" in raw:
                continue
            due_match = _DUE.search(raw)
            text = _DUE.sub("", raw).strip()
            if not text:
                continue
            entry = found.setdefault(
                _normalize(text), {"text": text, "due": due_match.group(1) if due_match else None, "sources": []}
            )
            source = relative.as_posix()
            if source not in entry["sources"]:
                entry["sources"].append(source)

    tasks, repeated = [], []
    for entry in found.values():
        if len(entry["sources"]) >= REPEAT_THRESHOLD:
            repeated.append({"text": entry["text"], "files": len(entry["sources"])})
            continue
        # sources are in sorted path order, which for daily notes is
        # chronological — the last one is the most recent mention.
        tasks.append({"text": entry["text"], "due": entry["due"], "source": entry["sources"][-1]})

    return {"tasks": tasks, "excluded_repeated": repeated}
