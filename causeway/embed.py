"""Deterministic stand-in embedding: hashed bag-of-words, 384 dims, L2-normalised.

No model download, fully offline and reproducible, so `make seed` is fast.
It is lexical (shared words => similar vectors), not semantic. The real
sentence-transformers model can replace `embed()` at eval time; the dimension
matches the vector index (384).
"""
import hashlib
import math
import re

DIM = 384
_TOKEN = re.compile(r"[a-z0-9_]+")


def embed(text: str) -> list[float]:
    vec = [0.0] * DIM
    for tok in _TOKEN.findall(text.lower()):
        h = hashlib.md5(tok.encode()).digest()
        idx = int.from_bytes(h[:4], "big") % DIM
        vec[idx] += 1.0 if h[4] % 2 == 0 else -1.0
    norm = math.sqrt(sum(x * x for x in vec))
    return [x / norm for x in vec] if norm else vec
