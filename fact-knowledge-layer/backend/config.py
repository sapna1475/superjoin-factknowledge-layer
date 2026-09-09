import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/factlayer"
)

# Hugging Face Inference API - no local model weights, no GPU required.
HF_API_TOKEN = os.environ.get("HF_API_TOKEN", "")
HF_API_URL = "https://router.huggingface.co/hf-inference/models"
HF_LLM_MODEL = os.environ.get("HF_LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
HF_EMBEDDING_MODEL = os.environ.get("HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
HF_NLI_MODEL = os.environ.get("HF_NLI_MODEL", "cross-encoder/nli-deberta-v3-small")
