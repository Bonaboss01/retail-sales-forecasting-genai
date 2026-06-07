# upload_forecasts_to_supabase.py
#
# Uploads weekly_forecasts.csv to core.fact_weekly_forecasts in Supabase.
# Safe to run multiple times — duplicates are ignored via ON CONFLICT DO NOTHING.
#
# Usage:
#   PYTHONPATH=. python3 src/forecasting/upload_forecasts_to_supabase.py

import os
from urllib.parse import quote_plus
from uuid import uuid4

import pandas as pd
from sqlalchemy import create_engine, text

FORECAST_PATH = "data/outputs/weekly_forecasts.csv"
TABLE_NAME    = "fact_weekly_forecasts"
SCHEMA        = "core"
BATCH_SIZE    = 5000

# ── DB connection ──────────────────────────────────────────────────────────────
host     = "aws-1-eu-central-1.pooler.supabase.com"
port     = 5432
database = "postgres"
user     = "postgres.ogkdfmkybqtrsglcizzt"
password = quote_plus(os.getenv("SUPABASE_DB_PASSWORD", ""))

if not password:
    raise ValueError("SUPABASE_DB_PASSWORD environment variable is not set.")

engine = create_engine(
    f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}",
    pool_pre_ping=True,
    pool_recycle=300,
)


# ── Ensure unique index exists ─────────────────────────────────────────────────
def ensure_unique_index():
    index_name = f"ux_{TABLE_NAME}_week_store_product_model"
    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE UNIQUE INDEX IF NOT EXISTS {index_name}
            ON {SCHEMA}.{TABLE_NAME} (week_start, store_id, product_id, model_version);
        """))


# ── Upload in safe batches ─────────────────────────────────────────────────────
def upload(df: pd.DataFrame):
    total   = len(df)
    columns = list(df.columns)
    col_sql = ", ".join([f'"{c}"' for c in columns])

    print(f"Uploading {total:,} rows → {SCHEMA}.{TABLE_NAME}")

    for start in range(0, total, BATCH_SIZE):
        end   = min(start + BATCH_SIZE, total)
        batch = df.iloc[start:end].copy()
        temp  = f"tmp_{TABLE_NAME}_{uuid4().hex[:10]}"

        with engine.begin() as conn:
            batch.to_sql(temp, con=conn, schema=SCHEMA,
                         if_exists="replace", index=False, chunksize=1000)
            conn.execute(text(f"""
                INSERT INTO {SCHEMA}.{TABLE_NAME} ({col_sql})
                SELECT {col_sql} FROM {SCHEMA}.{temp}
                ON CONFLICT DO NOTHING;
            """))
            conn.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.{temp};"))

        print(f"  Uploaded rows {start + 1:,} – {end:,}")

    print(f"Done — {SCHEMA}.{TABLE_NAME} is up to date.")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print(f"Loading {FORECAST_PATH} ...")
    df = pd.read_csv(FORECAST_PATH)
    df["week_start"]          = pd.to_datetime(df["week_start"]).dt.date
    df["forecast_created_at"] = pd.to_datetime(df["forecast_created_at"]).dt.date
    df["store_id"]            = df["store_id"].astype(str)
    df["product_id"]          = pd.to_numeric(df["product_id"], errors="coerce").astype(int)
    df["predicted_units"]     = pd.to_numeric(df["predicted_units"], errors="coerce")

    print(f"Rows loaded    : {len(df):,}")
    print(f"Forecast weeks : {df['week_start'].nunique()}")
    print(f"Date range     : {df['week_start'].min()} → {df['week_start'].max()}")
    print()

    # Create table from structure if it doesn't exist yet
    with engine.begin() as conn:
        df.head(0).to_sql(TABLE_NAME, con=conn, schema=SCHEMA,
                          if_exists="append", index=False)

    ensure_unique_index()
    upload(df)


if __name__ == "__main__":
    main()
