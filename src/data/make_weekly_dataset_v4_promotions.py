# make_weekly_dataset_v4_promotions.py
#
# Builds the weekly training dataset for model v4 (with promotion features).
# Pulls everything from Supabase — no CSV files read or written.
#
# Usage (standalone):
#   python src/data/make_weekly_dataset_v4_promotions.py
#
# Usage (from train script):
#   from src.data.make_weekly_dataset_v4_promotions import build_weekly_base

import warnings
import pandas as pd
from src.data.db_connection import run_query

warnings.filterwarnings("ignore")


# ── Load raw tables from Supabase ─────────────────────────

def load_sales() -> pd.DataFrame:
    return run_query("""
        SELECT
            s.date, s.store_id, s.product_id,
            s.units_sold, s.price, s.regular_price, s.discount_pct,
            s.promo_flag, s.starting_inventory,
            c.season
        FROM core.fact_sales s
        LEFT JOIN core.dim_calendar c ON s.date = c.date
        ORDER BY s.date ASC
    """)


def load_promotions() -> pd.DataFrame:
    return run_query("""
        SELECT date, store_id, product_id,
               promo_flag, discount_pct, promo_type
        FROM core.fact_promotions
    """)


def load_calendar() -> pd.DataFrame:
    return run_query("""
        SELECT date, year, month, week_of_year,
               season, is_weekend, is_holiday, is_payday,
               is_black_friday_period
        FROM core.dim_calendar
        ORDER BY date ASC
    """)


# ── Prepare and aggregate weekly sales ────────────────────

def build_weekly_sales(sales: pd.DataFrame) -> pd.DataFrame:
    df = sales.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["store_id"] = df["store_id"].astype(str)
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["product_id"])
    df["product_id"] = df["product_id"].astype(int)

    iso = df["date"].dt.isocalendar()
    df["year"] = iso.year.astype(int)
    df["week"] = iso.week.astype(int)
    df["week_start"] = df["date"] - pd.to_timedelta(df["date"].dt.weekday, unit="D")
    df["month_calendar"] = df["date"].dt.month
    df["quarter"] = df["date"].dt.quarter
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    df["black_friday_week"] = df["date"].dt.month.eq(11) & df["date"].dt.weekday.eq(4)

    weekly = df.groupby(
        ["week_start", "year", "week", "store_id", "product_id"],
        as_index=False
    ).agg(
        units_sold              =("units_sold",          "sum"),
        avg_price               =("price",               "mean"),
        avg_regular_price       =("regular_price",       "mean"),
        avg_discount_pct        =("discount_pct",        "mean"),
        avg_starting_inventory  =("starting_inventory",  "mean"),
        month                   =("month_calendar",      "first"),
        quarter                 =("quarter",             "first"),
        week_of_year            =("week_of_year",        "first"),
        black_friday_week       =("black_friday_week",   "max"),
        season                  =("season",              "first"),
    )

    return weekly


# ── Prepare and aggregate weekly promotions ───────────────

def build_weekly_promo_features(promotions: pd.DataFrame) -> pd.DataFrame:
    df = promotions.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["store_id"] = df["store_id"].astype(str)
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["product_id"])
    df["product_id"] = df["product_id"].astype(int)
    df["promo_flag"] = pd.to_numeric(df["promo_flag"], errors="coerce").fillna(0).astype(int)
    df["discount_pct"] = pd.to_numeric(df["discount_pct"], errors="coerce").fillna(0)
    df["promo_type"] = df["promo_type"].fillna("No Promo")

    iso = df["date"].dt.isocalendar()
    df["year"] = iso.year.astype(int)
    df["week"] = iso.week.astype(int)

    # Aggregate promo stats per week × store × product
    promo_weekly = df.groupby(
        ["year", "week", "store_id", "product_id"], as_index=False
    ).agg(
        promo_days_in_week      =("promo_flag",    "sum"),
        avg_weekly_discount_pct =("discount_pct",  "mean"),
        has_promo_week          =("promo_flag",     "max"),
    )

    # One-hot encode promo types and max per week
    type_dummies = pd.get_dummies(df["promo_type"], prefix="promo_type")
    df_with_types = pd.concat(
        [df[["year", "week", "store_id", "product_id"]].reset_index(drop=True),
         type_dummies.reset_index(drop=True)],
        axis=1
    )
    type_weekly = df_with_types.groupby(
        ["year", "week", "store_id", "product_id"], as_index=False
    ).max()

    promo_weekly = promo_weekly.merge(
        type_weekly, on=["year", "week", "store_id", "product_id"], how="left"
    )

    return promo_weekly


# ── Merge weekly sales + promo features ───────────────────

def merge_datasets(weekly: pd.DataFrame, promo_weekly: pd.DataFrame) -> pd.DataFrame:
    df = weekly.merge(
        promo_weekly,
        on=["year", "week", "store_id", "product_id"],
        how="left"
    )

    df["promo_days_in_week"]      = df["promo_days_in_week"].fillna(0)
    df["avg_weekly_discount_pct"] = df["avg_weekly_discount_pct"].fillna(0)
    df["has_promo_week"]          = df["has_promo_week"].fillna(0)

    for col in [c for c in df.columns if c.startswith("promo_type_")]:
        df[col] = df[col].fillna(0)

    return df


# ── Public entry point ────────────────────────────────────

def build_weekly_base() -> pd.DataFrame:
    """
    Pull data from Supabase and return the v4 weekly training DataFrame.
    No CSV files written anywhere.
    """
    print("Loading sales from Supabase...")
    sales = load_sales()

    print("Loading promotions from Supabase...")
    promotions = load_promotions()

    print("Building weekly sales aggregation...")
    weekly = build_weekly_sales(sales)

    print("Building weekly promotion features...")
    promo_weekly = build_weekly_promo_features(promotions)

    print("Merging datasets...")
    df = merge_datasets(weekly, promo_weekly)

    print(f"Done. Weekly dataset: {len(df):,} rows | {df.shape[1]} columns")
    return df


# ── Standalone run ────────────────────────────────────────

if __name__ == "__main__":
    df = build_weekly_base()
    print(df.head())
    print(df.dtypes)
