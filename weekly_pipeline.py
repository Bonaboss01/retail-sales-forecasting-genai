# weekly_pipeline.py
#
# Full weekly orchestration — runs inside the Vertex AI container every Saturday.
# Steps:
#   1. Generate new sales data and upload to BigQuery
#   2. Generate next week's forecast using the best model
#   3. Upload forecast to BigQuery
#
# Usage (local):
#   PYTHONPATH=. python3 weekly_pipeline.py
#
# In production this is triggered automatically by the Vertex AI schedule.

import sys
from datetime import datetime


def log(msg: str):
    print(f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def run_data_pipeline():
    log("STEP 1 — Generating and uploading sales data to BigQuery...")
    import generate_upload_to_bigquery as data_pipeline
    data_pipeline.main()
    log("STEP 1 — Done.")


def run_forecast():
    log("STEP 2 — Generating weekly forecast...")
    from src.forecasting.generate_weekly_forecast import main as forecast_main
    forecast_main()
    log("STEP 2 — Done.")


def run_forecast_upload():
    log("STEP 3 — Uploading forecast to BigQuery...")
    from src.forecasting.upload_forecasts_to_bigquery import main as upload_main
    upload_main()
    log("STEP 3 — Done.")


if __name__ == "__main__":
    log("=== Weekly pipeline started ===")
    try:
        run_data_pipeline()
        run_forecast()
        run_forecast_upload()
        log("=== Weekly pipeline complete ===")
    except Exception as e:
        log(f"Pipeline failed: {e}")
        sys.exit(1)
