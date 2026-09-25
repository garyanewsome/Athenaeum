import os

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://192.168.1.157:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
CHROMA_DIR = os.environ.get("CHROMA_DIR", "./chroma_data")
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "vault")

VAULT_REPO_URL = os.environ.get("VAULT_REPO_URL", "git@github.com:garyanewsome/obsidian-vault.git")
VAULT_REPO_PATH = os.environ.get("VAULT_REPO_PATH", "./vault-repo")

# Where /tasks looks for open checkboxes. Just daily notes on purpose: the
# rest of the vault has checkboxes in song/project notes that are working
# notes, not things to chase (found by surveying the real vault).
TASKS_SCAN_FOLDER = os.environ.get("TASKS_SCAN_FOLDER", "00 System/Daily Notes")
