import json

from . import config, hf_client, llm

EXPLAIN_PROMPT = """Two facts were extracted from different documents.

Fact A: {a}
Fact B: {b}

A classifier labeled their relationship as: {label}

Decide the true relationship - one of "corroborates", "contradicts", or
"reconciled" (they look different but are both true, e.g. because of
different time periods, units, or scope). Explain your reasoning in one or
two sentences, naming the specific difference if reconciled.

Return only JSON: {{"relation_type": "...", "explanation": "...", "confidence": 0.0}}
"""


def classify(text_a, text_b):
    """Cheap first pass via a small NLI model: is this pair even worth an
    LLM call? Filters out unrelated fact pairs before paying for generation."""
    result = hf_client.query(
        config.HF_NLI_MODEL,
        {"inputs": {"text": text_a, "text_pair": text_b}, "options": {"wait_for_model": True}},
    )
    scores = result[0] if isinstance(result[0], list) else result
    best = max(scores, key=lambda s: s["score"])
    return best["label"].lower(), float(best["score"])


def explain(fact_a, fact_b, label):
    """Only called for entailment/contradiction pairs - the expensive step,
    deliberately gated behind the NLI filter above."""
    prompt = EXPLAIN_PROMPT.format(a=json.dumps(fact_a), b=json.dumps(fact_b), label=label)
    try:
        result = json.loads(llm.generate(prompt))
        return result["relation_type"], result["explanation"], float(result.get("confidence", 0.5))
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
