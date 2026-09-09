import pymupdf


def extract_pages(pdf_path):
    """Return [{"page": 1, "text": "..."}, ...]. Streams page by page so
    large PDFs don't need to be loaded into memory at once."""
    doc = pymupdf.open(pdf_path)
    try:
        return [{"page": i + 1, "text": page.get_text()} for i, page in enumerate(doc)]
    finally:
        doc.close()
