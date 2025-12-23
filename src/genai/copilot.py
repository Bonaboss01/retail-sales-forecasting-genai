# src/genai/copilot.py
from __future__ import annotations
from typing import Dict, Any, List
from .tools import predict_revenue, predict_stockout
from .rag_qa import retrieve_contexts, answer_from_context

def route(query: str) -> str:
    q = query.lower()
    if any(k in q for k in ["stockout", "out of stock", "risk"]):
        return "stockout"
    if any(k in q for k in ["revenue", "forecast", "predict", "demand"]):
        return "forecast"
    return "rag"

def run_copilot(query: str, payload: Dict[str, Any], docs: List[Dict]) -> Dict[str, Any]:
    r = route(query)

    if r == "stockout":
        tool_res = predict_stockout(payload)
        return {"type": "tool", "tool": tool_res.tool, "result": tool_res.output}

    if r == "forecast":
        tool_res = predict_revenue(payload)
        return {"type": "tool", "tool": tool_res.tool, "result": tool_res.output}

    ctx = retrieve_contexts(query, docs)
    ans = answer_from_context(query, ctx)
    return {"type": "rag", "answer": ans, "sources": [c.get("title") for c in ctx]}
