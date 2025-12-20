"""
predict.py

Unified prediction interface for SunnyBest.

- Loads saved models from /models
- Builds the same features used during training
- Returns:
  - revenue forecast
  - stockout risk (probability)
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional

import joblib
import pandas as pd
import numpy as np

from src.data.make_dataset import build_merged_dataset
from src.features.build_features import build_forecast_features, build_stockout_features


MODEL_DIR = Path("models")
FORECAST_MODEL_PATH = MODEL_DIR / "xgb_revenue_forecast.pkl"
STOCKOUT_MODEL_PATH = MODEL_DIR / "stockout_classifier.pkl"


def load_models() -> Dict[str, Any]:
    """
    Load trained models from disk.
    """
    if not FORECAST_MODEL_PATH.exists():
        raise FileNotFoundError(f"Missing forecast model: {FORECAST_MODEL_PATH}")
    if not STOCKOUT_MODEL_PATH.exists():
        raise FileNotFoundError(f"Missing stockout model: {STOCKOUT_MODEL_PATH}")

    forecast_model = joblib.load(FORECAST_MODEL_PATH)
    stockout_model = joblib.load(STOCKOUT_MODEL_PATH)

    return {
        "forecast_model": forecast_model,
        "stockout_model": stockout_model
    }


def _align_columns(X_new: pd.DataFrame, X_ref: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure one-hot encoded columns match training columns:
    - add missing cols with 0
    - drop extra cols
    - order same as training
    """
    X_new = X_new.copy()

    missing_cols = [c for c in X_ref.columns if c not in X_new.columns]
    for c in missing_cols:
        X_new[c] = 0

    extra_cols = [c for c in X_new.columns if c not in X_ref.columns]
    if extra_cols:
        X_new = X_new.drop(columns=extra_cols)

    return X_new[X_ref.columns]


def predict_from_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Predict revenue and stockout risk from a single input row.

    Expected keys in row (minimum):
      - price
      - regular_price
      - discount_pct
      - promo_flag
      - month
      - is_weekend
      - is_holiday
      - is_payday
      - category
      - store_size
      - temperature_c
      - rainfall_mm
      - starting_inventory   (for stockout)

    NOTE:
    In deployment, these will come from your request payload + your feature pipeline.
    """
    models = load_models()
    forecast_model = models["forecast_model"]
    stockout_model = models["stockout_model"]

    df_one = pd.DataFrame([row])

    # Build features using the same functions used during training
    X_forecast, _ = build_forecast_features(df_one.assign(revenue=0), target="revenue")
    X_stockout, _ = build_stockout_features(df_one.assign(stockout_occurred=0), target="stockout_occurred")

    # Align columns using training reference columns stored in model (if available)
    # If not stored, we fallback by building reference columns from full dataset.
    # (This keeps things working before we add model pipelines.)
    try:
        X_ref_forecast = pd.DataFrame(columns=forecast_model.get_booster().feature_names)
        X_forecast = _align_columns(X_forecast, X_ref_forecast)
    except Exception:
        full_df = build_merged_dataset(save=False)
        X_ref_forecast, _yref = build_forecast_features(full_df, target="revenue")
        X_forecast = _align_columns(X_forecast, X_ref_forecast)

    try:
        X_ref_stock = pd.DataFrame(columns=stockout_model.get_booster().feature_names)
        X_stockout = _align_columns(X_stockout, X_ref_stock)
    except Exception:
        full_df = build_merged_dataset(save=False)
        X_ref_stock, _yref = build_stockout_features(full_df, target="stockout_occurred")
        X_stockout = _align_columns(X_stockout, X_ref_stock)

    # Predict
    revenue_pred = float(forecast_model.predict(X_forecast)[0])

    # Probability of stockout (positive class)
    stockout_proba = float(stockout_model.predict_proba(X_stockout)[0, 1])

    return {
        "predicted_revenue": revenue_pred,
        "stockout_probability": stockout_proba
    }


def predict_example_from_existing_data(
    date: Optional[str] = None,
    store_id: Optional[int] = None,
    product_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Convenience function:
    pick a real row from df and predict on it (good for sanity checking).
    """
    df = build_merged_dataset(save=False)

    if date is not None:
        df = df[df["date"] == pd.to_datetime(date)]
    if store_id is not None:
        df = df[df["store_id"] == store_id]
    if product_id is not None:
        df = df[df["product_id"] == product_id]

    if len(df) == 0:
        raise ValueError("No matching row found for the given filters.")

    row = df.iloc[0].to_dict()

    # Keep only fields needed for prediction
    needed = [
        "price", "regular_price", "discount_pct", "promo_flag",
        "month", "is_weekend", "is_holiday", "is_payday",
        "category", "store_size", "temperature_c", "rainfall_mm",
        "starting_inventory"
    ]
    payload = {k: row.get(k) for k in needed}

    return {
        "input_row": payload,
        "prediction": predict_from_row(payload)
    }


if __name__ == "__main__":
    # quick sanity check
    result = predict_example_from_existing_data()
    print("✅ Example prediction:")
    print(result)
