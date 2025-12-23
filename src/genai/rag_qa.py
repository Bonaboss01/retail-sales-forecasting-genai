from __future__ import annotations
from typing import List, Dict
import re

def retrieve_contexts(query: str, docs: List[Dict]) -> List[Dict]:
    """
    Naive retrieval: keyword overlap.
    Replace later with embeddings/FAISS.
    """
    q = set(re.findall(r"[a-zA-Z]+", query.lower()))
    scored = []
    for d in docs:
        words = set(re.findall(r"[a-zA-Z]+", (d.get("text","")).lower()))
        score = len(q & words)
        scored.append((score, d))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for s, d in scored if s > 0][:3] or docs[:1]

def answer_from_context(query: str, contexts: List[Dict]) -> str:
    top = contexts[0]
    return f"From the analysis ({top.get('title','doc')}): {top.get('text','')[:400]}..."
