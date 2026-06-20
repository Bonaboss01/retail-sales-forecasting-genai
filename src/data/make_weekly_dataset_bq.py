# make_weekly_dataset_bq.py
#
# BigQuery replacement for make_weekly_dataset_v2.py + make_weekly_dataset_v3_calendar.py.
# Reads fact_sales and dim_calendar from BigQuery, outputs the same
# weekly_sales_v3_calendar.csv that the training scripts expect.
#
# Usage:
#   PYTHONPATH=. python3 src/data/make_weekly_dataset_bq.py

import os
import pandas as pd
from google.cloud import bigquery

PROJECT_ID  = "sfs-dev-498722"
DATASET_ID  = "sunnybest"
OUTPUT_PATH = "data/processed/weekly_sales_v3_calendar.csv"

client = bigquery.Client(project=PROJECT_ID)


def load_sales() -> pd.DataFrame:
    print("Loading fact_sales from BigQuery...")
    return client.query(f"""
        SELECT
            date, store_id, product_id,
            units_sold, price, regular_price,
            discount_pct, promo_flag, starting_inventory
        FROM `{PROJECT_ID}.{DATASET_ID}.fact_sales`
    """).to_dataframe()


def load_calendar() -> pd.DataFrame:
    print("Loading dim_calendar from BigQuery...")
    return client.query(f"""
        SELECT
            date, year, month, season,
            is_holiday, is_payday, is_weekend, is_black_friday_period
        FROM `{PROJECT_ID}.{DATASET_ID}.dim_calendar`
    """).to_dataframe()


def build_weekly_sales(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"]       = pd.to_datetime(df["date"])
    df["store_id"]   = df["store_id"].astype(str)
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["date", "product_id", "units_sold"])
    df["product_id"] = df["product_id"].astype(int)
    df = df[df["units_sold"] >= 0].copy()

    for col in ["price", "regular_price", "discount_pct", "promo_flag", "starting_inventory"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    iso          = df["date"].dt.isocalendar()
    df["year"]   = iso.year.astype(int)
    df["week"]   = iso.week.astype(int)

    weekly = df.groupby(
        ["year", "week", "store_id", "product_id"], as_index=False
    ).agg(
        units_sold              =("units_sold",          "sum"),
        avg_price               =("price",               "mean"),
        avg_regular_price       =("regular_price",       "mean"),
        avg_discount_pct        =("discount_pct",        "mean"),
        promo_intensity         =("promo_flag",          "mean"),
        avg_starting_inventory  =("starting_inventory",  "mean"),
    )

    weekly["week_start"] = pd.to_datetime(
        weekly["year"].astype(str) + "-W" + weekly["week"].astype(str).str.zfill(2) + "-1",
        format="%G-W%V-%u"
    )
    weekly["month"]        = weekly["week_start"].dt.month
    weekly["quarter"]      = weekly["week_start"].dt.quarter
    weekly["week_of_year"] = weekly["week_start"].dt.isocalendar().week.astype(int)

    return weekly.sort_values(["store_id", "product_id", "week_start"]).reset_index(drop=True)


def build_calendar_weekly(cal: pd.DataFrame) -> pd.DataFrame:
    cal = cal.copy()
    cal["date"] = pd.to_datetime(cal["date"])

    for col in ["is_holiday", "is_payday", "is_weekend", "is_black_friday_period"]:
        cal[col] = cal[col].astype(int)

    iso          = cal["date"].dt.isocalendar()
    cal["year"]  = iso.year.astype(int)
    cal["week"]  = iso.week.astype(int)

    return cal.groupby(["year", "week"], as_index=False).agg(
        holiday_days_in_week    =("is_holiday",              "sum"),
        payday_days_in_week     =("is_payday",               "sum"),
        weekend_days_in_week    =("is_weekend",              "sum"),
        black_friday_week       =("is_black_friday_period",  "max"),
        season                  =("season",                  "first"),
    )


def build_dataset() -> pd.DataFrame:
    sales  = load_sales()
    cal    = load_calendar()

    print("Aggregating to weekly sales...")
    weekly = build_weekly_sales(sales)

    print("Aggregating calendar features...")
    cal_wk = build_calendar_weekly(cal)

    print("Merging...")
    df = weekly.merge(cal_wk, on=["year", "week"], how="left")
    df["season"] = df["season"].fillna("unknown")

    print(f"\nRows     : {len(df):,}")
    print(f"Stores   : {df['store_id'].nunique()}")
    print(f"Products : {df['product_id'].nunique()}")
    print(f"Date range: {df['week_start'].min()} → {df['week_start'].max()}")

    return df


if __name__ == "__main__":
    df = build_dataset()
    print(df.head())
