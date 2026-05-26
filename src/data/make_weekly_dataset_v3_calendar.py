# make_weekly_dataset_v3_calendar.py

import os
import pandas as pd
from src.data.db_connection import get_engine


# -----------------------------
# Config
# -----------------------------
WEEKLY_V2_PATH = "data/processed/weekly_sales_v2.csv"
OUTPUT_PATH = "data/processed/weekly_sales_v3_calendar.csv"

CALENDAR_QUERY = "SELECT * FROM core.dim_calendar"


# -----------------------------
# Load Data
# -----------------------------
def load_weekly_v2(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def load_calendar() -> pd.DataFrame:
    engine = get_engine()
    return pd.read_sql(CALENDAR_QUERY, engine)


# -----------------------------
# Prepare Calendar Weekly
# -----------------------------
def prepare_calendar_weekly(calendar: pd.DataFrame) -> pd.DataFrame:
    calendar = calendar.copy()

    calendar["date"] = pd.to_datetime(calendar["date"], errors="coerce")
    calendar = calendar.dropna(subset=["date"])

    iso = calendar["date"].dt.isocalendar()
    calendar["year"] = iso.year.astype(int)
    calendar["week"] = iso.week.astype(int)

    # Convert booleans to int
    calendar["is_weekend"] = calendar["is_weekend"].astype(int)
    calendar["is_holiday"] = calendar["is_holiday"].astype(int)
    calendar["is_payday"] = calendar["is_payday"].astype(int)
    calendar["is_black_friday_period"] = calendar["is_black_friday_period"].astype(int)

    calendar_weekly = calendar.groupby(
        ["year", "week"],
        as_index=False
    ).agg(
        holiday_days_in_week=("is_holiday", "sum"),
        payday_days_in_week=("is_payday", "sum"),
        weekend_days_in_week=("is_weekend", "sum"),
        black_friday_week=("is_black_friday_period", "max"),
        month=("month", "first"),
        season=("season", "first"),
    )

    return calendar_weekly


# -----------------------------
# Merge
# -----------------------------
def merge_datasets(
    df_weekly: pd.DataFrame,
    calendar_weekly: pd.DataFrame
) -> pd.DataFrame:
    df = df_weekly.merge(
        calendar_weekly,
        on=["year", "week"],
        how="left",
        suffixes=("", "_calendar")
    )

    # Fill missing values
    numeric_cols = [
        "holiday_days_in_week",
        "payday_days_in_week",
        "weekend_days_in_week",
        "black_friday_week"
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["season"] = df["season"].fillna("unknown")

    return df


# -----------------------------
# Save
# -----------------------------
def save_output(df: pd.DataFrame, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)


# -----------------------------
# Main
# -----------------------------
def main():
    print("Loading weekly v2 dataset...")
    df_weekly = load_weekly_v2(WEEKLY_V2_PATH)

    print("Loading calendar data...")
    calendar = load_calendar()

    print("Preparing calendar weekly features...")
    calendar_weekly = prepare_calendar_weekly(calendar)

    print("Merging datasets...")
    df_v3 = merge_datasets(df_weekly, calendar_weekly)

    print("Saving weekly v3 dataset...")
    save_output(df_v3, OUTPUT_PATH)

    print(f"\nSaved to: {OUTPUT_PATH}")
    print(f"Rows: {len(df_v3):,}")
    print(df_v3.head())


if __name__ == "__main__":
    main()