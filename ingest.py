"""Manual ingest of a local folder of markdown notes into the vector store.

Stands in for the eventual K8s CronJob that pulls the Obsidian vault's
private GitHub repo and diffs against the last-seen commit. For now,
just point it at a local folder:

    python ingest.py ./sample_vault
"""

import sys
from pathlib import Path

from app.chunking import chunk_markdown
from app.embeddings import embed
from app.store import add_chunks


def ingest_folder(folder: Path) -> None:
    md_files = sorted(folder.rglob("*.md"))
    if not md_files:
        print(f"No .md files found under {folder}")
        return

    for path in md_files:
        text = path.read_text(encoding="utf-8")
        chunks = chunk_markdown(text)
        if not chunks:
            continue

        ids = [f"{path}:{i}" for i in range(len(chunks))]
        embeddings = [embed(chunk) for chunk in chunks]
        metadatas = [{"source": str(path)} for _ in chunks]

        add_chunks(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
        print(f"Ingested {len(chunks)} chunk(s) from {path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python ingest.py <folder>")
        sys.exit(1)

    ingest_folder(Path(sys.argv[1]))
