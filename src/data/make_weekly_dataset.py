# make_weekly_dataset.py

import os
import pandas as pd
from src.data.db_connection import get_engine


# -----------------------------
# Config
# -----------------------------
QUERY = "SELECT * FROM core.fact_sales"
OUTPUT_PATH = "data/processed/weekly_sales.csv"


# -----------------------------
# Load Data
# -----------------------------
def load_data() -> pd.DataFrame:
    engine = get_engine()
    return pd.read_sql(QUERY, engine)


# -----------------------------
# Clean Data
# -----------------------------
def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    # Keep only needed columns
    cols = ["date", "store_id", "product_id", "units_sold"]
    df = df[cols].copy()

    # Convert date
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Drop rows with missing critical fields
    df = df.dropna(subset=["date", "store_id", "product_id", "units_sold"])

    # Ensure units_sold is numeric
    df["units_sold"] = pd.to_numeric(df["units_sold"], errors="coerce")
    df = df.dropna(subset=["units_sold"])

    # Remove invalid negative sales
    df = df[df["units_sold"] >= 0].copy()

    return df


# -----------------------------
# Create Weekly Dataset
# -----------------------------
def make_weekly_dataset(df: pd.DataFrame) -> pd.DataFrame:
    # Create ISO year and week
    iso_calendar = df["date"].dt.isocalendar()
    df["year"] = iso_calendar.year.astype(int)
    df["week"] = iso_calendar.week.astype(int)

    # Aggregate to weekly level
    df_weekly = df.groupby(
        ["year", "week", "store_id", "product_id"],
        as_index=False
    ).agg({
        "units_sold": "sum"
    })

    # Create week_start date (Monday of ISO week)
    df_weekly["week_start"] = pd.to_datetime(
        df_weekly["year"].astype(str) + "-W" + df_weekly["week"].astype(str).str.zfill(2) + "-1",
        format="%G-W%V-%u"
    )

    # Sort for consistency
    df_weekly = df_weekly.sort_values(
        ["store_id", "product_id", "week_start"]
    ).reset_index(drop=True)

    return df_weekly


# -----------------------------
# Save Output
# -----------------------------
def save_output(df_weekly: pd.DataFrame, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_weekly.to_csv(output_path, index=False)


# -----------------------------
# Main
# -----------------------------
def main() -> None:
    print("Loading fact_sales from PostgreSQL...")
    df = load_data()

    print("Cleaning daily sales data...")
    df = clean_data(df)

    print("Aggregating to weekly dataset...")
    df_weekly = make_weekly_dataset(df)

    print("Saving weekly dataset...")
    save_output(df_weekly, OUTPUT_PATH)

    print("\nDone.")
    print(f"Weekly dataset saved to: {OUTPUT_PATH}")
    print(f"Rows: {len(df_weekly):,}")
    print("\nPreview:")
    print(df_weekly.head())


if __name__ == "__main__":
    main()