"""
FastAPI app for SunnyBest Retail Demand Intelligence System.

Endpoints:
- GET  /health
- POST /predict  -> revenue forecast + stockout probability
- GET  /predict/example -> run prediction using a real row from merged df
"""

from __future__ import annotations

from typing import Optional, Dict, Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.models.predict import predict_from_row, predict_example_from_existing_data

from src.genai.copilot import run_copilot


app = FastAPI(
    title="AI-Powered Retail Decision Intelligence Platform",
    version="1.0.0",
    description="Forecast revenue and predict stockout risk. Built from the SunnyBest project pipeline."
)


# -----------------------------
# Request / Response Schemas
# -----------------------------
class PredictRequest(BaseModel):
    # Pricing
    price: float = Field(..., ge=0)
    regular_price: float = Field(..., ge=0)
    discount_pct: float = Field(0, ge=0, le=100)
    promo_flag: int = Field(0, ge=0, le=1)

    # Time
    month: int = Field(..., ge=1, le=12)
    is_weekend: int = Field(0, ge=0, le=1)
    is_holiday: int = Field(0, ge=0, le=1)
    is_payday: int = Field(0, ge=0, le=1)

    # Product / Store
    category: str
    store_size: str

    # Weather
    temperature_c: float
    rainfall_mm: float

    # Inventory (needed for stockout model)
    starting_inventory: int = Field(..., ge=0)


class PredictResponse(BaseModel):
    predicted_revenue: float
    stockout_probability: float


# -----------------------------
# Routes
# -----------------------------
@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    payload = req.model_dump()
    out = predict_from_row(payload)
    return PredictResponse(**out)


@app.get("/predict/example")
def predict_example(
    date: Optional[str] = None,
    store_id: Optional[int] = None,
    product_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Example usage:
    /predict/example
    /predict/example?store_id=1
    /predict/example?product_id=1001
    /predict/example?date=2024-12-25&store_id=1&product_id=1001
    """
    return predict_example_from_existing_data(date=date, store_id=store_id, product_id=product_id)


# minimal docs store (later we load from files)
DOCS: List[dict] = [
    {"title": "Promo uplift summary", "text": "Promotions show uplift strongest in Mobile Phones and Accessories..."},
    {"title": "Stockout model summary", "text": "Stockouts increase with high demand, promotions, and low starting inventory..."},
    {"title": "Pricing optimisation summary", "text": "Pricing simulation suggests revenue responds to price changes differently by category..."},
]

class AskRequest(BaseModel):
    query: str
    payload: Optional[Dict[str, Any]] = None

@app.post("/ask")
def ask(req: AskRequest):
    payload = req.payload or {}
    return run_copilot(req.query, payload, DOCS)


