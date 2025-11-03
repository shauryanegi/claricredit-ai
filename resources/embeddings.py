import requests
from typing import List
from resources.config import config

BASE_URL = config.EMBEDDING_BASE_URL
EMBEDDING_MODEL = config.EMBEDDING_MODEL

def get_embedding(text: str) -> List[float]:
    """Get embedding for text using Ollama nomic-embed-text."""
    url = f"{BASE_URL}/api/embeddings"
    payload = {"model": EMBEDDING_MODEL, "prompt": text, "options": {
                "num_ctx": 8192
            }}
    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["embedding"]
