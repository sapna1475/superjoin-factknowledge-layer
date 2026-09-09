from . import config, hf_client


def embed(text):
    result = hf_client.query(
        config.HF_EMBEDDING_MODEL,
        {"inputs": text, "options": {"wait_for_model": True}},
    )
    return _to_vector(result)


def _to_vector(result):
    """The API returns a pooled sentence vector for most sentence-transformers
    models, but occasionally returns per-token vectors instead - mean-pool
    those into one vector so callers always get a flat list of floats."""
    if isinstance(result, list) and len(result) == 1 and isinstance(result[0], list):
        result = result[0]
    if isinstance(result, list) and result and isinstance(result[0], list):
        return [sum(col) / len(col) for col in zip(*result)]
    return result
