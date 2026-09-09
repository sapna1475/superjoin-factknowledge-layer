import time

import requests
from huggingface_hub import InferenceClient

from . import config
_client = InferenceClient(token=config.HF_API_TOKEN, provider="featherless-ai")


def query(model, payload, retries=3):
    """Free HF models unload when idle, so the first call after a while can
    return a 503 with an estimated load time instead of a result. Retrying
    once or twice covers this without the caller needing to know about it."""
    url = f"{config.HF_API_URL}/{model}"
    headers = {"Authorization": f"Bearer {config.HF_API_TOKEN}"}
    resp = None
    for attempt in range(retries):
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code == 503 and attempt < retries - 1:
            time.sleep(resp.json().get("estimated_time", 10))
            continue
        break
    resp.raise_for_status()
    return resp.json()


def chat(model, messages, max_tokens=700):
    """Uses the official huggingface_hub client, which picks a working
    inference provider automatically instead of guessing a raw URL."""
    completion = _client.chat_completion(
        messages=messages,
        model=model,
        max_tokens=max_tokens,
    )
    return {
        "choices": [
            {"message": {"content": completion.choices[0].message.content}}
        ]
    }