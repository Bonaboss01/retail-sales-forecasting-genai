from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
import joblib
import numpy as np

FORECAST_MODEL_PATH = "models/xgb_revenue_forecast.pkl"
STOCKOUT_MODEL_PATH = "models/stockout_classifier.pkl"

@dataclass
class ToolResult:
    tool: str
    output: Dict[str, Any]

def load_models():
    forecast_model = joblib.load(FORECAST_MODEL_PATH)
    stockout_model = joblib.load(STOCKOUT_MODEL_PATH)
    return forecast_model, stockout_model

def predict_stockout(features: Dict[str, Any]) -> ToolResult:
    _, stockout_model = load_models()

    # IMPORTANT: must match your training feature order
    feature_order = [
        "price", "discount_pct", "promo_flag", "month",
        "is_weekend", "is_holiday", "is_payday",
        "temperature_c", "rainfall_mm", "starting_inventory",
    ]

    x = np.array([[features.get(f, 0) for f in feature_order]])
    proba = float(stockout_model.predict_proba(x)[0, 1])
    band = "High" if proba >= 0.7 else "Medium" if proba >= 0.4 else "Low"

    return ToolResult(
        tool="predict_stockout",
        output={"stockout_probability": proba, "stockout_risk_band": band}
    )

def predict_revenue(features: Dict[str, Any]) -> ToolResult:
    forecast_model, _ = load_models()

    feature_order = [
        "price", "regular_price", "discount_pct", "promo_flag", "month",
        "is_weekend", "is_holiday", "is_payday",
        "temperature_c", "rainfall_mm", "starting_inventory",
    ]
    x = np.array([[features.get(f, 0) for f in feature_order]])
    yhat = float(forecast_model.predict(x)[0])

    return ToolResult(
        tool="predict_revenue",
        output={"predicted_revenue": yhat}
    )
