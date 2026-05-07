# generate_weekly_forecast.py
#
# Generates a one-week-ahead forecast using the current best model.
# Loads data from Supabase — no CSV files needed.
# Best model is read automatically from model_registry.csv.
#
# Usage:
#   PYTHONPATH=. python src/forecasting/generate_weekly_forecast.py

import os
import warnings

import joblib
import pandas as pd

from src.data.make_weekly_dataset_v4_promotions import build_weekly_v4

warnings.filterwarnings("ignore")


# ── Config ────────────────────────────────────────────────
REGISTRY_PATH  = "models/model_registry.csv"
FORECAST_PATH  = "data/outputs/weekly_forecasts.csv"
TARGET         = "units_sold"


# ── Load best model from registry ────────────────────────

def load_best_model():
    if not os.path.exists(REGISTRY_PATH):
        raise FileNotFoundError(f"Registry not found: {REGISTRY_PATH}")

    registry = pd.read_csv(REGISTRY_PATH, comment="#")
    best = registry[registry["status"] == "best"]

    if best.empty:
        raise ValueError("No model marked as 'best' in model_registry.csv.")

    model_version = best.iloc[0]["model_version"]
    model_path    = best.iloc[0]["model_path"]

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    print(f"Best model : {model_version}")
    print(f"Model path : {model_path}")

    return joblib.load(model_path), model_version


# ── Feature engineering ───────────────────────────────────

def create_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["store_id", "product_id", "week_start"]).copy()
    group = ["store_id", "product_id"]
    df["lag_1"]          = df.groupby(group)[TARGET].shift(1)
    df["lag_4"]          = df.groupby(group)[TARGET].shift(4)
    df["rolling_mean_4"] = df.groupby(group)[TARGET].shift(1).rolling(4).mean()
    return df


# ── Build next-week feature rows ──────────────────────────

def build_future_rows(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["store_id", "product_id", "week_start"]).copy()

    last_date = df["week_start"].max()
    next_week = last_date + pd.Timedelta(days=7)

    print(f"Last data week  : {last_date.date()}")
    print(f"Forecasting week: {next_week.date()}")

    # Take the last known state per store × product
    future = df.groupby(["store_id", "product_id"], as_index=False).last().copy()
    future["week_start"]   = next_week
    future["year"]         = next_week.year
    future["week"]         = int(next_week.isocalendar().week)
    future["week_of_year"] = int(next_week.isocalendar().week)
    future["month"]        = next_week.month
    future["quarter"]      = (next_week.month - 1) // 3 + 1

    # Assume no promotion for next week (can be overridden externally)
    for col in ["promo_days_in_week", "avg_weekly_discount_pct", "has_promo_week"]:
        if col in future.columns:
            future[col] = 0

    for col in [c for c in future.columns if c.startswith("promo_type_")]:
        future[col] = 0

    # Drop rows without sufficient lag history
    future = future.dropna(subset=["lag_1", "lag_4", "rolling_mean_4"]).copy()
    return future


# ── Encode and align to model features ───────────────────

def encode_and_align(future: pd.DataFrame, model) -> pd.DataFrame:
    cat_cols = [c for c in ["season", "store_id", "product_id"] if c in future.columns]
    encoded  = pd.get_dummies(future, columns=cat_cols, drop_first=True)

    model_features = model.feature_names_in_

    # Add any missing columns as 0
    for col in model_features:
        if col not in encoded.columns:
            encoded[col] = 0

    encoded = encoded[model_features].copy()

    # Coerce types
    for col in encoded.columns:
        if encoded[col].dtype == "bool":
            encoded[col] = encoded[col].astype(int)
        elif encoded[col].dtype == "object":
            encoded[col] = pd.to_numeric(encoded[col], errors="coerce").fillna(0)

    return encoded


# ── Save forecast (append, deduplicate) ───────────────────

def save_forecast(df: pd.DataFrame, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if os.path.exists(path):
        old = pd.read_csv(path)
        old["week_start"] = pd.to_datetime(old["week_start"], errors="coerce")
        df = pd.concat([old, df], ignore_index=True)
        df = df.drop_duplicates(
            subset=["week_start", "store_id", "product_id", "model_version"],
            keep="last"
        )

    df.to_csv(path, index=False)
    print(f"Forecast saved : {path}  ({len(df):,} total rows)")


# ── Main ──────────────────────────────────────────────────

def main() -> None:
    print("Loading best model from registry...")
    model, model_version = load_best_model()

    print("\nLoading weekly dataset from Supabase...")
    df = build_weekly_v4()

    df["week_start"] = pd.to_datetime(df["week_start"])
    df["store_id"]   = df["store_id"].astype(str)
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce").astype(int)
    df[TARGET]       = pd.to_numeric(df[TARGET], errors="coerce").fillna(0)
    df               = df[df[TARGET] >= 0].copy()

    print("\nComputing lag features...")
    df = create_lag_features(df)

    print("\nBuilding next-week rows...")
    future = build_future_rows(df)

    print("\nEncoding and aligning to model features...")
    X_future = encode_and_align(future, model)

    print("Generating predictions...")
    future["predicted_units"] = model.predict(X_future).round(2)

    forecast_output = future[["week_start", "store_id", "product_id", "predicted_units"]].copy()
    forecast_output["forecast_created_at"] = pd.Timestamp.today().normalize()
    forecast_output["model_version"]       = model_version

    print(f"\nForecast rows: {len(forecast_output):,}")
    print(forecast_output.head(10).to_string(index=False))

    print("\nSaving forecast...")
    save_forecast(forecast_output, FORECAST_PATH)

    print("\nDone.")


if __name__ == "__main__":
    main()
