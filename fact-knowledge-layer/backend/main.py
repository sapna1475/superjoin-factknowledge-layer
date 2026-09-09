import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile

from . import db, pipeline

app = FastAPI(title="Fact Knowledge Layer")


@app.on_event("startup")
def startup():
    db.init_schema()


@app.post("/documents")
async def upload_document(file: UploadFile):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        document_id, fact_count = pipeline.process_document(tmp_path, file.filename)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return {"document_id": document_id, "facts_extracted": fact_count}


@app.get("/documents")
def get_documents():
    return db.list_documents()


@app.get("/facts")
def get_facts(document_id: Optional[int] = None):
    return db.list_facts(document_id)


@app.get("/relations")
def get_relations(relation_type: Optional[str] = None):
    return db.list_relations(relation_type)
