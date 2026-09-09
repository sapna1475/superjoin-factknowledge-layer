import json

from . import llm

PROMPT = """You are extracting factual claims from one page of a document.
List every distinct factual claim: numbers, dates, statuses, or relationships
between entities. Skip opinions.

For each fact return an object with:
- subject: what or who the fact is about
- predicate: the attribute or relationship being stated
- value: the fact's value, as stated
- unit: unit of measurement, if any, else null
- time_scope: the time period the fact applies to, if stated, else null
- quote: the exact sentence or phrase supporting this fact, copied verbatim
- confidence: 0 to 1

Return only a JSON array. Return [] if there are no facts.

Text:
\"\"\"
{text}
\"\"\"
"""


def extract_facts(page_text):
    if not page_text.strip():
        return []
    raw = llm.generate(PROMPT.format(text=page_text[:4000]))
    try:
        facts = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(facts, list):
        return []
    return [f for f in facts if isinstance(f, dict) and f.get("quote")]


def is_grounded(fact, page_text):
    """A fact is grounded only if its quote genuinely appears in the source
    page. This is what catches hallucinated citations instead of trusting
    the model's claim blindly."""
    normalize = lambda s: " ".join(s.split()).lower()
    return normalize(fact.get("quote", "")) in normalize(page_text)
