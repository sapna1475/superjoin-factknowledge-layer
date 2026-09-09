import re

import requests


def generate(prompt):
    resp = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": "qwen2.5:3b-instruct",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        },
        timeout=120,
    )
    resp.raise_for_status()
    text = resp.json()["message"]["content"]
    return _extract_json(text)


def _extract_json(text):
    """Free instruct models don't reliably follow 'return only JSON' the way
    Claude does - pull out the first JSON array or object instead of trusting
    the whole response body to parse cleanly."""
    match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
    return match.group(1) if match else text
