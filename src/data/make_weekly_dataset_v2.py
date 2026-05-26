# make_weekly_dataset_v2.py

import os
import pandas as pd
from src.data.db_connection import get_engine


QUERY = "SELECT * FROM core.fact_sales"
OUTPUT_PATH = "data/processed/weekly_sales_v2.csv"


def load_data() -> pd.DataFrame:
    engine = get_engine()
    return pd.read_sql(QUERY, engine)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "date",
        "store_id",
        "product_id",
        "units_sold",
        "price",
        "regular_price",
        "discount_pct",
        "promo_flag",
        "starting_inventory",
    ]
    df = df[cols].copy()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "store_id", "product_id", "units_sold"])

    numeric_cols = [
        "units_sold",
        "price",
        "regular_price",
        "discount_pct",
        "promo_flag",
        "starting_inventory",
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["units_sold"])
    df = df[df["units_sold"] >= 0].copy()

    df["price"] = df["price"].fillna(0)
    df["regular_price"] = df["regular_price"].fillna(0)
    df["discount_pct"] = df["discount_pct"].fillna(0)
    df["promo_flag"] = df["promo_flag"].fillna(0)
    df["starting_inventory"] = df["starting_inventory"].fillna(0)

    return df


def make_weekly_dataset(df: pd.DataFrame) -> pd.DataFrame:
    iso = df["date"].dt.isocalendar()
    df["year"] = iso.year.astype(int)
    df["week"] = iso.week.astype(int)

    df_weekly = df.groupby(
        ["year", "week", "store_id", "product_id"],
        as_index=False
    ).agg(
        units_sold=("units_sold", "sum"),
        avg_price=("price", "mean"),
        avg_regular_price=("regular_price", "mean"),
        avg_discount_pct=("discount_pct", "mean"),
        promo_intensity=("promo_flag", "mean"),
        avg_starting_inventory=("starting_inventory", "mean"),
    )

    df_weekly["week_start"] = pd.to_datetime(
        df_weekly["year"].astype(str)
        + "-W"
        + df_weekly["week"].astype(str).str.zfill(2)
        + "-1",
        format="%G-W%V-%u"
    )

    df_weekly["month"] = df_weekly["week_start"].dt.month
    df_weekly["quarter"] = df_weekly["week_start"].dt.quarter
    df_weekly["week_of_year"] = df_weekly["week_start"].dt.isocalendar().week.astype(int)

    df_weekly = df_weekly.sort_values(
        ["store_id", "product_id", "week_start"]
    ).reset_index(drop=True)

    return df_weekly


def save_output(df_weekly: pd.DataFrame, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_weekly.to_csv(output_path, index=False)


def main() -> None:
    print("Loading fact_sales from PostgreSQL...")
    df = load_data()

    print("Cleaning data...")
    df = clean_data(df)

    print("Creating weekly v2 dataset...")
    df_weekly = make_weekly_dataset(df)

    print("Saving output...")
    save_output(df_weekly, OUTPUT_PATH)

    print(f"\nSaved to: {OUTPUT_PATH}")
    print(f"Rows: {len(df_weekly):,}")
    print(df_weekly.head())


if __name__ == "__main__":
    main()