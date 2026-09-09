# Fact Knowledge Layer

Extracts facts from PDFs, grounds each one in the exact source text it came
from, and figures out how facts across different documents relate to each
other — corroborating, contradicting, or reconcilable through context like
time period, units, or scope.

## Demo Video
![Demo](assets/Demo%20Video.mp4)

## Architecture

![Architecture](assets/architecture.svg)


**Ingest**: a PDF is parsed page by page (PyMuPDF), each page is sent to a
free hosted LLM to extract factual claims as flexible JSON, and each claim
is checked against the source text to confirm it isn't hallucinated.

**Index**: every fact is embedded (free hosted embedding model) and stored
in Postgres, which also builds a full-text index on it. Two search paths,
one database.

**Compare**: when a new fact arrives, hybrid search (keyword + semantic,
merged with reciprocal rank fusion) finds related facts already in the
store. A small NLI model cheaply screens each pair — only pairs that look
like entailment or contradiction get escalated to an LLM call that writes
the actual explanation. Neutral pairs are dropped without ever touching the
expensive model.

**Serve**: FastAPI exposes documents, facts, and relations; a minimal
Streamlit page lets you upload a PDF and browse the results.

### Why these specific choices

- **Hugging Face Inference API, not local models.** No GPU, no multi-GB
  model downloads, no Ollama process to keep running. Extraction and
  explanation use a hosted instruct LLM; embeddings and NLI classification
  use small hosted models. The trade-off: free-tier models can be slower to
  follow strict "return only JSON" instructions than a model like Claude,
  so responses are parsed defensively (see `backend/llm.py`), and cold model
  starts are retried automatically (see `backend/hf_client.py`).
- **Postgres, not a separate vector database.** `pgvector` gives us
  semantic search and native full-text search (`tsvector`) in the same
  database as the relational data (documents, facts, relations). A fact
  belongs to a document, a relation joins two facts — that's a natural fit
  for foreign keys and joins, not for a second, separate vector store that
  would need to be kept in sync by hand.
- **JSONB for fact data, not fixed columns.** A revenue fact needs a unit
  and a time period; a director fact needs a role and a date range. Storing
  `data` as JSONB means new fact shapes just show up — no migration needed.
- **NLI model before LLM, not LLM for every pair.** Classifying a pair as
  entailment/contradiction/neutral with a small model is far cheaper than a
  generative call. The LLM is only used to write an explanation, and only
  for pairs the classifier flagged as interesting.

## Setup and Run Instructions

**Requirements**: Python 3.11+, Docker, a free
[Hugging Face account and access token](https://huggingface.co/settings/tokens).

```bash
# 1. Start Postgres with pgvector
docker compose up -d

# 2. Install dependencies
pip install -r requirements.txt


# 4. Run the API (creates tables on first start)
uvicorn backend.main:app --reload

# 5. In a second terminal (with the same venv active), run the UI
streamlit run ui/app.py
```

The `.env` file is loaded automatically by both the API and the UI — no manual export step needed on any OS.

Open the Streamlit URL it prints, upload a PDF, and browse the extracted
facts and relations. The API alone is also usable directly, e.g.
`curl -F file=@document.pdf http://localhost:8000/documents`.

**Note on the free tier**: Hugging Face's free Inference API models
unload when idle, so the first call after a while can take 10-20 seconds
while the model reloads — this is handled automatically with a retry, not
a bug if the first upload feels slow. Model names are configurable in
`.env` if a specific model becomes unavailable on the free tier.



## Approach

The pipeline is deliberately linear and inspectable: parse → extract →
ground → embed → index → (for each new fact) hybrid search → classify →
explain → store. Every fact keeps its page number and verbatim quote, so
every claim in the UI can be traced back to the exact sentence it came
from — that traceability was treated as more important than extraction
recall.

**The four required cases**, as they show up in this system:
1. **Corroboration** — two facts with high hybrid-search similarity, NLI
   labels them as entailment, and the LLM confirms they're the same claim
   phrased differently (e.g. "$4.2M" vs "4.2 million dollars").
2. **Contradiction** — similar subject/predicate, different values, and the
   LLM finds no reconciling context (different time period, unit, or scope)
   that would explain the difference.
3. **Reconciled** — looks like a contradiction on the surface (same figure,
   different value), but the LLM's explanation names the actual difference,
   e.g. one fact is annual revenue and the other is a single quarter.
4. **Failure case** — the grounding check is what surfaces this: if the
   model's `quote` field doesn't appear verbatim in the source page, the
   fact is stored but flagged as ungrounded rather than silently trusted.
   The Streamlit UI shows this warning inline on any such fact.

**AI tools used**: Claude (Anthropic) was used throughout for architecture
discussion, code generation, and debugging during development.

## Limitations and Next Steps

- Free-tier instruct models are noticeably less reliable than Claude at
  strict JSON output — malformed responses are currently just dropped
  rather than retried with a repair prompt. A retry-with-error-feedback
  loop would recover more of these.
- Postgres full-text ranking (`ts_rank`) approximates BM25 but isn't
  identical to it — fine at this scale, but a dedicated BM25 index would
  rank keyword matches more precisely at higher fact volumes.
- No async ingestion queue yet — a large PDF or a slow model response
  blocks the upload request. A background worker (e.g. Redis + RQ) would
  let uploads return immediately.
- Only tested with a handful of documents. `pgvector`'s HNSW index should
  hold up well into the hundreds of thousands of facts, and dedicated
  vector databases (e.g. Qdrant) would be the natural next step past that.
- Incremental ingestion and the evolving JSONB schema both work by
  construction (new documents are only ever compared against, never
  reprocess, existing facts) but haven't been stress-tested at scale.

## Additional Notes

The Hugging Face free-tier model catalog changes over time — if a
configured model (see `.env.example`) is no longer available, swap in a
currently available instruct/embedding/NLI model of the same shape; no
code changes should be needed.
