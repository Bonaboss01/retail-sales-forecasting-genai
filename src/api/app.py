from __future__ import annotations

import os
from typing import Optional, Dict, Any, List

import pandas as pd
from fastapi import FastAPI

from src.api.routes import predict, decision, agents
from src.genai.schemas import AskRequest, AskResponse
from src.genai.router import route_question


app = FastAPI(
    title="SunnyBest Retail Forecasting System",
    version="2.0.0",
    description=(
        "AI-powered retail forecasting, pricing optimisation, "
        "inventory planning and GenAI decision support for SunnyBest Telecommunications."
    ),
)

# ── Register routers ──────────────────────────────────────
app.include_router(predict.router,  tags=["predict"])
app.include_router(decision.router, tags=["decision"])
app.include_router(agents.router,   tags=["agents"])

# ── Elasticity table (loaded once) ───────────────────────
ELASTICITY_PATH = os.getenv("ELASTICITY_PATH", "data/processed/elasticity_by_category.csv")


def load_elasticity_table() -> pd.DataFrame:
    if os.path.exists(ELASTICITY_PATH):
        return pd.read_csv(ELASTICITY_PATH)
    return pd.DataFrame(columns=["category", "price_elasticity"])


# ── RAG knowledge docs ────────────────────────────────────
DOCS: List[dict] = [
    {
        "title": "Promo uplift summary",
        "text": "Promotions show strongest uplift in Mobile Phones and Accessories.",
    },
    {
        "title": "Stockout model summary",
        "text": "Stockouts increase with high demand, active promotions, and low starting inventory.",
    },
    {
        "title": "Pricing optimisation summary",
        "text": "Profit-optimised pricing with margin floor 15%: constrained scipy optimisation per category.",
    },
    {
        "title": "Units sold definition",
        "text": "units_sold is the weekly total units of a product sold at a given store.",
    },
    {
        "title": "Model registry",
        "text": "The best model is weekly_model_v3_calendar with WAPE ~15% on the 2026 holdout.",
    },
]


# ── Core endpoints ────────────────────────────────────────

@app.get("/health", tags=["system"])
def health() -> Dict[str, Any]:
    return {"status": "ok", "app": "SunnyBest SFS", "version": "2.0.0"}


@app.get("/pricing/elasticity", tags=["pricing"])
def get_elasticity(category: Optional[str] = None) -> Dict[str, Any]:
    df = load_elasticity_table()

    if df.empty:
        return {
            "items": [],
            "note": "Elasticity table not found. Run build_elasticity_artifact.py first.",
        }

    if category:
        df = df[df["category"] == category]

    return {"items": df.to_dict(orient="records")}


@app.post("/ask", response_model=AskResponse, tags=["genai"])
def ask(req: AskRequest) -> AskResponse:
    answer = route_question(
        question=req.question,
        payload=req.payload,
        docs=DOCS,
    )
    return AskResponse(answer=answer)
