"""
make_dataset.py

Builds the canonical merged dataset (df) for SunnyBest.

- Loads raw CSVs from data/raw/
- Deduplicates promos (1 row per date-store-product)
- Merges sales + products + stores + calendar + weather (+ promos_event)
- Writes merged output to data/processed/ (optional)

Single source of truth for downstream notebooks, models, API, and dashboard.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


# -----------------------------
# Helpers
# -----------------------------
def _project_root(start: Optional[Path] = None) -> Path:
    """Find repo root by walking up until we see data/ and src/."""
    cur = (start or Path.cwd()).resolve()
    for _ in range(15):
        if (cur / "data").exists() and (cur / "src").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return (start or Path.cwd()).resolve()


def _read_csv(path: Path, parse_dates: Optional[list[str]] = None) -> pd.DataFrame:
    """Read CSV with safer dtype inference for large files."""
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return pd.read_csv(path, parse_dates=parse_dates, low_memory=False)


def _standardise_date_col(df: pd.DataFrame, col: str = "date") -> pd.DataFrame:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def _ensure_city_column(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Ensure a dataframe has a column named exactly 'city' (case/variant tolerant)."""
    if "city" in df.columns:
        return df

    lower_map = {c.lower(): c for c in df.columns}
    for cand in ["city", "store_city", "town", "location"]:
        if cand in lower_map:
            return df.rename(columns={lower_map[cand]: "city"})

    raise ValueError(f"{name} must contain a 'city' column (or variant). Found columns: {df.columns.tolist()}")


def _normalise_city(s: pd.Series) -> pd.Series:
    """Normalise city strings so joins are reliable."""
    return (
        s.astype(str)
        .str.strip()
        .str.lower()
        .replace({"nan": np.nan, "none": np.nan})
    )


# -----------------------------
# Main builder
# -----------------------------
def build_merged_dataset(
    raw_dir: Optional[str | Path] = None,
    processed_dir: Optional[str | Path] = None,
    save: bool = True,
    filename: str = "sunnybest_merged_df.csv",
) -> pd.DataFrame:
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

    # ---- Standardise dates
    sales = _standardise_date_col(sales)
    calendar = _standardise_date_col(calendar)
    weather = _standardise_date_col(weather)
    promos = _standardise_date_col(promos)

    # ---- Validate required keys
    required_sales_cols = {"date", "store_id", "product_id"}
    missing = required_sales_cols - set(sales.columns)
    if missing:
        raise ValueError(f"Sales is missing required columns: {missing}")

    # ---- Ensure city columns exist (handles 'City' vs 'city')
    stores = _ensure_city_column(stores, "Stores")
    weather = _ensure_city_column(weather, "Weather")

    # -------------------------------------------------------
    # Align join key types (THIS FIXES YOUR PROMOS MERGE ERROR)
    # -------------------------------------------------------
    # Keep identifiers as strings everywhere for consistent joins.
    for df_ in (sales, stores, promos):
        df_["store_id"] = df_["store_id"].astype(str)

    for df_ in (sales, products, promos):
        df_["product_id"] = df_["product_id"].astype(str)

    # ---- Normalise city values for reliable joins
    stores["city"] = _normalise_city(stores["city"])
    weather["city"] = _normalise_city(weather["city"])

    # ---- CRITICAL: prevent city_x/city_y by removing city from sales if it exists
    # (We want stores to be the source of truth for store location)
    if "city" in sales.columns:
        sales = sales.drop(columns=["city"])

    # ---- Deduplicate promotions to 1 row per date-store-product
    if len(promos) > 0:
        promos = (
            promos.sort_values(["date", "store_id", "product_id"])
                  .drop_duplicates(subset=["date", "store_id", "product_id"], keep="last")
        )

    # ---- Merge step-by-step
    df = sales.merge(products, on="product_id", how="left")
    df = df.merge(stores, on="store_id", how="left")          # brings in 'city'
    df = df.merge(calendar, on="date", how="left")

    print("City columns in df:", [c for c in df.columns if "city" in c.lower()])

    if "city" not in df.columns:
        raise KeyError(
            "df has no 'city' after merging stores. "
            "This usually means store_id keys don't match or stores city column wasn't mapped correctly."
        )

    # ---- Merge weather on date + city
    df = df.merge(weather, on=["date", "city"], how="left")

    # ---- Merge promotions (rename to avoid collisions)
    if len(promos) > 0:
        promos_renamed = promos.rename(columns={
            "promo_type": "promo_type_event",
            "discount_pct": "discount_pct_event",
            "promo_flag": "promo_flag_event",
        })

        # Safety check (helps you debug instantly if types drift again)
        for k in ["store_id", "product_id"]:
            if df[k].dtype != promos_renamed[k].dtype:
                raise TypeError(f"Dtype mismatch on {k}: df={df[k].dtype}, promos={promos_renamed[k].dtype}")

        df = df.merge(promos_renamed, on=["date", "store_id", "product_id"], how="left")
    else:
        df["promo_type_event"] = np.nan
        df["discount_pct_event"] = 0.0
        df["promo_flag_event"] = 0

    # ---- Clean promo event fields
    df["promo_flag_event"] = df["promo_flag_event"].fillna(0).astype(int)
    df["discount_pct_event"] = df["discount_pct_event"].fillna(0)

    # ---- Save
    if save:
        proc_path.mkdir(parents=True, exist_ok=True)
        out_file = proc_path / filename
        df.to_csv(out_file, index=False)
        print(f"✅ Saved merged dataset: {out_file}")

    return df


if __name__ == "__main__":
    _ = build_merged_dataset(save=True)
