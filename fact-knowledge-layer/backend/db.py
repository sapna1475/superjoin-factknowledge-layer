import json
from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector

from . import config


def get_conn():
    conn = psycopg.connect(config.DATABASE_URL, autocommit=True)
    try:
        register_vector(conn)
    except psycopg.ProgrammingError:
        pass  # vector extension not created yet - happens only before init_schema()
    return conn


def init_schema():
    schema = (Path(__file__).parent / "schema.sql").read_text()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(schema)


def insert_document(filename, page_count):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO documents (filename, page_count) VALUES (%s, %s) RETURNING id",
            (filename, page_count),
        )
        return cur.fetchone()[0]


def list_documents():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, filename, page_count, uploaded_at FROM documents ORDER BY id")
        return [
            {"id": r[0], "filename": r[1], "page_count": r[2], "uploaded_at": r[3].isoformat()}
            for r in cur.fetchall()
        ]


def insert_fact(document_id, page, quote, grounded, data, embedding):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO facts (document_id, page, quote, grounded, data, embedding, search_text)
               VALUES (%s, %s, %s, %s, %s, %s, to_tsvector('english', %s))
               RETURNING id""",
            (document_id, page, quote, grounded, json.dumps(data), embedding, quote),
        )
        return cur.fetchone()[0]


def _fact_row(row):
    id_, document_id, page, quote, grounded, data, filename = row
    return {
        "id": id_,
        "document_id": document_id,
        "page": page,
        "quote": quote,
        "grounded": grounded,
        "data": data,
        "filename": filename,
    }


_FACT_SELECT = """
    SELECT f.id, f.document_id, f.page, f.quote, f.grounded, f.data, d.filename
    FROM facts f JOIN documents d ON d.id = f.document_id
"""


def get_fact(fact_id):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(_FACT_SELECT + " WHERE f.id = %s", (fact_id,))
        row = cur.fetchone()
        return _fact_row(row) if row else None


def list_facts(document_id=None):
    with get_conn() as conn, conn.cursor() as cur:
        if document_id:
            cur.execute(_FACT_SELECT + " WHERE f.document_id = %s ORDER BY f.id", (document_id,))
        else:
            cur.execute(_FACT_SELECT + " ORDER BY f.id")
        return [_fact_row(r) for r in cur.fetchall()]


def keyword_search(query, exclude_fact_id, limit=10):
    words = query.split()
    if not words:
        return []
    search_str = " OR ".join(words)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT id FROM facts
               WHERE id != %s AND search_text @@ websearch_to_tsquery('english', %s)
               ORDER BY ts_rank(search_text, websearch_to_tsquery('english', %s)) DESC
               LIMIT %s""",
            (exclude_fact_id, search_str, search_str, limit),
        )
        return [r[0] for r in cur.fetchall()]


def vector_search(embedding, exclude_fact_id, limit=10):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT id FROM facts WHERE id != %s
               ORDER BY embedding <=> %s::vector LIMIT %s""",
            (exclude_fact_id, embedding, limit),
        )
        return [r[0] for r in cur.fetchall()]


def insert_relation(fact_a_id, fact_b_id, relation_type, explanation, confidence):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO relations (fact_a_id, fact_b_id, relation_type, explanation, confidence)
               VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (fact_a_id, fact_b_id, relation_type, explanation, confidence),
        )
        return cur.fetchone()[0]


def list_relations(relation_type=None):
    query = "SELECT id, fact_a_id, fact_b_id, relation_type, explanation, confidence FROM relations"
    params = ()
    if relation_type:
        query += " WHERE relation_type = %s"
        params = (relation_type,)
    query += " ORDER BY id DESC"
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
    return [
        {
            "id": r[0],
            "fact_a": get_fact(r[1]),
            "fact_b": get_fact(r[2]),
            "relation_type": r[3],
            "explanation": r[4],
            "confidence": r[5],
        }
        for r in rows
    ]
