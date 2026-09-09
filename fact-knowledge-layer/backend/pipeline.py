from . import compare, db, embeddings, extractor, parser, search


def process_document(pdf_path, filename):
    pages = parser.extract_pages(pdf_path)
    document_id = db.insert_document(filename, len(pages))

    new_facts = []  # (fact_id, text, embedding, raw_data)
    for page in pages:
        for raw in extractor.extract_facts(page["text"]):
            grounded = extractor.is_grounded(raw, page["text"])
            text = search.fact_text(raw)
            vector = embeddings.embed(text)
            fact_id = db.insert_fact(document_id, page["page"], raw["quote"], grounded, raw, vector)
            new_facts.append((fact_id, text, vector, raw))

    # Compare each new fact only against what's already in the index - this
    # is what makes adding a new document incremental: existing facts are
    # never re-read or re-embedded.
    for fact_id, text, vector, raw in new_facts:
        for candidate_id in search.hybrid_search(text, vector, fact_id):
            candidate = db.get_fact(candidate_id)
            label, _ = compare.classify(text, search.fact_text(candidate["data"]))
            if label == "neutral":
                continue
            result = compare.explain(raw, candidate["data"], label)
            if result is None:
                continue
            relation_type, explanation, confidence = result
            db.insert_relation(fact_id, candidate_id, relation_type, explanation, confidence)

    return document_id, len(new_facts)
