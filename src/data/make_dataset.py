"""
make_dataset.py

Builds the canonical merged dataset (df) for SunnyBest.

- Loads raw CSVs from data/raw/
- Deduplicates promos (1 row per date-store-product)
- Merges sales + products + stores + calendar + weather (+ promos_event)
- Writes merged output to data/processed/ (optional)

This is the single source of truth for downstream notebooks, models, API, and dashboard.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


# -----------------------------
# Helpers
# -----------------------------
def _project_root(start: Optional[Path] = None) -> Path:
    """
    Find project root by walking up until we see key repo files/folders.
    This makes the code robust whether you run it from src/, notebooks/, or repo root.
    """
    if start is None:
        start = Path.cwd()

    markers = {"README.md", "data", "src", "requirements.txt", "pyproject.toml"}
    cur = start.resolve()

    for _ in range(10):  # enough levels for typical repos
        items = {p.name for p in cur.iterdir()} if cur.exists() else set()
        if markers.intersection(items) >= {"data", "src"}:
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent

    # fallback: current working directory
    return start.resolve()


def _read_csv(path: Path, parse_dates: Optional[list[str]] = None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return pd.read_csv(path, parse_dates=parse_dates)


def _standardise_date_col(df: pd.DataFrame, col: str = "date") -> pd.DataFrame:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


# -----------------------------
# Main builder
# -----------------------------
def build_merged_dataset(
    raw_dir: Optional[str | Path] = None,
    processed_dir: Optional[str | Path] = None,
    save: bool = True,
    filename: str = "sunnybest_merged_df.csv",
) -> pd.DataFrame:
    """
    Build and (optionally) save the merged dataset.

    Returns:
        df (pd.DataFrame): merged dataset
    """

    root = _project_root()
    raw_path = Path(raw_dir) if raw_dir is not None else root / "data" / "raw"
    proc_path = Path(processed_dir) if processed_dir is not None else root / "data" / "processed"

    # ---- Load raw datasets
    sales = _read_csv(raw_path / "sunnybest_sales.csv", parse_dates=["date"])
    products = _read_csv(raw_path / "sunnybest_products.csv")
    stores = _read_csv(raw_path / "sunnybest_stores.csv")
    calendar = _read_csv(raw_path / "sunnybest_calendar.csv", parse_dates=["date"])
    weather = _read_csv(raw_path / "sunnybest_weather.csv", parse_dates=["date"])
    promos = _read_csv(raw_path / "sunnybest_promotions.csv", parse_dates=["date"])

    # ---- Standardise date
    sales = _standardise_date_col(sales)
    calendar = _standardise_date_col(calendar)
    weather = _standardise_date_col(weather)
    promos = _standardise_date_col(promos)

    # ---- Defensive cleaning / expected keys
    required_sales_cols = {"date", "store_id", "product_id"}
    missing = required_sales_cols - set(sales.columns)
    if missing:
        raise ValueError(f"Sales is missing required columns: {missing}")

    # Ensure weather has city for merge
    if "city" not in weather.columns:
        raise ValueError("Weather dataset must contain 'city' column (keyed by date + city).")

    # Ensure stores has city (so df has city before weather merge)
    if "city" not in stores.columns:
        raise ValueError("Stores dataset must contain 'city' column (used to merge weather on date+city).")

    # ---- Deduplicate promotions to 1 row per date-store-product
    if len(promos) > 0:
        promos = (
            promos.sort_values(["date", "store_id", "product_id"])
                  .drop_duplicates(subset=["date", "store_id", "product_id"], keep="last")
        )

    # ---- Merge step-by-step (avoids suffix chaos)
    df = sales.merge(products, on="product_id", how="left")
    df = df.merge(stores, on="store_id", how="left")          # brings in 'city'
    df = df.merge(calendar, on="date", how="left")

    # ---- Merge weather on date + city (this is where your earlier KeyError happened)
    # At this point df MUST have 'city' (from stores). If not, we fail loudly.
    if "city" not in df.columns:
        raise KeyError(
            "df does not contain 'city' before weather merge. "
            "Check that stores has 'city' and the stores merge ran correctly."
        )

    df = df.merge(weather, on=["date", "city"], how="left")

    # ---- Merge promotions (rename to avoid collisions with sales promo fields)
    if len(promos) > 0:
        promos_renamed = promos.rename(columns={
            "promo_type": "promo_type_event",
            "discount_pct": "discount_pct_event",
            "promo_flag": "promo_flag_event",
        })
        df = df.merge(promos_renamed, on=["date", "store_id", "product_id"], how="left")
    else:
        df["promo_type_event"] = np.nan
        df["discount_pct_event"] = 0.0
        df["promo_flag_event"] = 0

    # ---- Clean promo event fields
    if "promo_flag_event" in df.columns:
        df["promo_flag_event"] = df["promo_flag_event"].fillna(0).astype(int)
    if "discount_pct_event" in df.columns:
        df["discount_pct_event"] = df["discount_pct_event"].fillna(0)

    # ---- Optional: ensure key business columns exist (helps downstream notebooks)
    # These checks are non-fatal but helpful.
    expected_cols = [
        "category", "season", "is_weekend", "is_holiday", "is_payday",
        "temperature_c", "rainfall_mm", "weather_condition"
    ]
    missing_expected = [c for c in expected_cols if c not in df.columns]
    if missing_expected:
        print(f"⚠️ Note: merged df is missing expected columns: {missing_expected}")

    # ---- Save to processed
    if save:
        proc_path.mkdir(parents=True, exist_ok=True)
        out_file = proc_path / filename
        df.to_csv(out_file, index=False)
        print(f"✅ Saved merged dataset: {out_file}")

    return df


# -----------------------------
# CLI entry (optional)
# -----------------------------
if __name__ == "__main__":
    # Running this file directly will generate the merged dataset into data/processed/
    _ = build_merged_dataset(save=True)
