from fastapi import FastAPI
from pydantic import BaseModel

from app.embeddings import embed
from app.store import query

app = FastAPI(title="Athenaeum")


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchMatch(BaseModel):
    text: str
    source: str | None
    distance: float


class SearchResponse(BaseModel):
    matches: list[SearchMatch]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
    query_embedding = embed(request.query)
    matches = query(query_embedding, top_k=request.top_k)
    return {"matches": matches}
