import chromadb

from app.config import CHROMA_DIR, COLLECTION_NAME

_client = chromadb.PersistentClient(path=CHROMA_DIR)
_collection = _client.get_or_create_collection(COLLECTION_NAME)


def add_chunks(ids: list[str], embeddings: list[list[float]], documents: list[str], metadatas: list[dict]) -> None:
    _collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)


def delete_by_source(source: str) -> None:
    _collection.delete(where={"source": source})


def query(embedding: list[float], top_k: int = 5) -> list[dict]:
    result = _collection.query(query_embeddings=[embedding], n_results=top_k)
    matches = []
    for document, metadata, distance in zip(
        result["documents"][0], result["metadatas"][0], result["distances"][0]
    ):
        matches.append({"text": document, "source": metadata.get("source"), "distance": distance})
    return matches
