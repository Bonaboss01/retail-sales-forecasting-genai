"""
build_features.py

Feature engineering for SunnyBest models.

- Takes merged df from make_dataset.py
- Builds model-ready feature matrices
- Keeps logic consistent across notebooks, training, API, and dashboards
"""

from __future__ import annotations

from typing import Tuple
import pandas as pd


# -----------------------------
# Feature selection helpers
# -----------------------------
def select_base_features(df: pd.DataFrame) -> pd.DataFrame:
    """Select core explanatory features (minimal transforms)."""

    feature_cols = [
        # pricing
        "price",
        "regular_price",
        "discount_pct",

        # promotion
        "promo_flag",

        # time
        "month",
        "is_weekend",
        "is_holiday",
        "is_payday",

        # product / store
        "category",
        "store_size",

        # weather
        "temperature_c",
        "rainfall_mm",
    ]

    existing = [c for c in feature_cols if c in df.columns]
    return df[existing].copy()


def encode_categoricals(X: pd.DataFrame) -> pd.DataFrame:
    """One-hot encode categorical variables; leave numeric columns unchanged."""
    cat_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()
    if not cat_cols:
        return X

    return pd.get_dummies(X, columns=cat_cols, drop_first=True)


# -----------------------------
# Forecasting features
# -----------------------------
def build_forecast_features(
    df: pd.DataFrame,
    target: str = "revenue",
) -> Tuple[pd.DataFrame, pd.Series]:
    """Build features and target for revenue forecasting."""

    if target not in df.columns:
        raise KeyError(f"Target column '{target}' not found in df")

    X = select_base_features(df)
    X = encode_categoricals(X)
    y = df[target]

    return X, y


# -----------------------------
# Stockout classification features
# -----------------------------
def build_stockout_features(
    df: pd.DataFrame,
    target: str = "stockout_occurred",
) -> Tuple[pd.DataFrame, pd.Series]:
    """Build features and target for stockout classification."""

    if target not in df.columns:
        raise KeyError(f"Target column '{target}' not found in df")

    feature_cols = [
        "price",
        "discount_pct",
        "promo_flag",
        "starting_inventory",
        "month",
        "is_weekend",
        "is_holiday",
        "category",
        "store_size",
    ]

    existing = [c for c in feature_cols if c in df.columns]
    X = df[existing].copy()
    X = encode_categoricals(X)
    y = df[target].astype(int)

    return X, y
