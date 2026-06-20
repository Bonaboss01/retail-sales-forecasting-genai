# upload_forecasts_to_bigquery.py
#
# Uploads weekly_forecasts.csv to sunnybest.fact_weekly_forecasts in BigQuery.
# Safe to run multiple times — duplicates are ignored via MERGE.
#
# Usage:
#   PYTHONPATH=. python3 src/forecasting/upload_forecasts_to_bigquery.py

from uuid import uuid4

import pandas as pd
from google.cloud import bigquery

FORECAST_PATH = "data/outputs/weekly_forecasts.csv"
PROJECT_ID    = "sfs-dev-498722"
DATASET_ID    = "sunnybest"
TABLE_NAME    = "fact_weekly_forecasts"
BATCH_SIZE    = 5000

TABLE_ID      = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_NAME}"
MERGE_KEYS    = ["week_start", "store_id", "product_id", "model_version"]

client = bigquery.Client(project=PROJECT_ID)


def table_exists() -> bool:
    from google.api_core.exceptions import NotFound
    try:
        client.get_table(TABLE_ID)
        return True
    except NotFound:
        return False


def upload(df: pd.DataFrame):
    total   = len(df)
    cols    = list(df.columns)
    print(f"Uploading {total:,} rows → {TABLE_ID} (appending new forecasts only)")

    for start in range(0, total, BATCH_SIZE):
        end     = min(start + BATCH_SIZE, total)
        batch   = df.iloc[start:end].copy()
        temp_id = f"{PROJECT_ID}.{DATASET_ID}.tmp_{TABLE_NAME}_{uuid4().hex[:8]}"

        job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
        job = client.load_table_from_dataframe(batch, temp_id, job_config=job_config)
        job.result()

        if not table_exists():
            client.copy_table(temp_id, TABLE_ID).result()
        else:
            merge_on    = " AND ".join([f"T.`{k}` = S.`{k}`" for k in MERGE_KEYS])
            insert_cols = ", ".join([f"`{c}`" for c in cols])
            insert_vals = ", ".join([f"S.`{c}`" for c in cols])
            client.query(f"""
                MERGE `{TABLE_ID}` T
                USING `{temp_id}` S
                ON {merge_on}
                WHEN NOT MATCHED THEN
                    INSERT ({insert_cols}) VALUES ({insert_vals})
            """).result()

        client.delete_table(temp_id, not_found_ok=True)
        print(f"  Rows {start + 1:,} – {end:,} done")

    print(f"Done — {TABLE_ID} is up to date.")


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

    upload(df)


if __name__ == "__main__":
    main()
