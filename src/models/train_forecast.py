"""
train_forecast.py

Train and save the revenue forecasting model for SunnyBest.
"""

from __future__ import annotations

from pathlib import Path
import joblib
import pandas as pd

from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

# project imports
from data.make_dataset import build_merged_dataset
from features.build_features import build_forecast_features


# -----------------------------
# Config
# -----------------------------
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(exist_ok=True)

MODEL_PATH = MODEL_DIR / "xgb_revenue_forecast.pkl"
RANDOM_STATE = 42


# -----------------------------
# Training
# -----------------------------
def train_forecast_model() -> dict:
    """
    Train XGBoost revenue forecast model and save it.
    Returns training metrics.
    """

    # Load data
    df = build_merged_dataset(save=False)

    # Build features
    X, y = build_forecast_features(df, target="revenue")

    # Train/validation split
    X_train, X_val, y_train, y_val = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=RANDOM_STATE
    )

    # Model
    model = XGBRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=RANDOM_STATE
    )

    # Fit
    model.fit(X_train, y_train)

    # Evaluate
    preds = model.predict(X_val)
    rmse = mean_squared_error(y_val, preds, squared=False)

    # Save
    joblib.dump(model, MODEL_PATH)

    print(f"✅ Forecast model saved to: {MODEL_PATH}")
    print(f"📉 Validation RMSE: {rmse:,.2f}")

    return {
        "rmse": rmse,
        "n_train": len(X_train),
        "n_val": len(X_val),
        "n_features": X.shape[1],
    }


# -----------------------------
# CLI entry
# -----------------------------
if __name__ == "__main__":
    metrics = train_forecast_model()
    print("Training summary:", metrics)
