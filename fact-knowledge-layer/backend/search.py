from . import db


def fact_text(data):
    """Flatten a fact's JSONB fields into one string for embedding and search."""
    return f"{data.get('subject', '')} {data.get('predicate', '')} {data.get('value', '')} {data.get('unit') or ''}"


def hybrid_search(query_text, query_embedding, exclude_fact_id, top_k=5, rrf_k=60):
    """Reciprocal rank fusion of Postgres full-text ranking (our BM25-like
    keyword signal) and pgvector cosine similarity (our semantic signal)."""
    keyword_ids = db.keyword_search(query_text, exclude_fact_id)
    vector_ids = db.vector_search(query_embedding, exclude_fact_id)

    scores = {}
    for rank, fid in enumerate(keyword_ids):
        scores[fid] = scores.get(fid, 0) + 1 / (rrf_k + rank + 1)
    for rank, fid in enumerate(vector_ids):
        scores[fid] = scores.get(fid, 0) + 1 / (rrf_k + rank + 1)

    ranked = sorted(scores, key=scores.get, reverse=True)
    return ranked[:top_k]
