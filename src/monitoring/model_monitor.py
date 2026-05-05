# model_monitor.py
#
# Compares weekly forecasts against actual sales from Supabase.
# Computes WAPE, bias, MAE per week and raises alerts when accuracy degrades.
#
# Usage:
#   python src/monitoring/model_monitor.py

import os
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.data.db_connection import run_query

warnings.filterwarnings("ignore")


# ── Config ────────────────────────────────────────────────
FORECAST_PATH        = "data/outputs/weekly_forecasts.csv"
OUTPUT_MONITOR_PATH  = "data/outputs/weekly_model_monitoring.csv"
OUTPUT_SUMMARY_PATH  = "data/outputs/weekly_monitoring_summary.csv"
PLOT_WAPE_PATH       = "data/outputs/plots/weekly_wape.png"
PLOT_ACTUAL_VS_PRED  = "data/outputs/plots/weekly_actual_vs_predicted.png"

WAPE_ALERT_THRESHOLD = 0.20   # flag weeks where WAPE > 20%


# ── Load forecasts (local CSV) ────────────────────────────

def load_forecasts(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No forecast file found at {path}. "
            "Run generate_weekly_forecast.py first."
        )
    df = pd.read_csv(path)
    df["week_start"]      = pd.to_datetime(df["week_start"], errors="coerce")
    df["store_id"]        = df["store_id"].astype(str)
    df["product_id"]      = pd.to_numeric(df["product_id"], errors="coerce").astype("Int64")
    df                    = df.dropna(subset=["week_start", "store_id", "product_id", "predicted_units"])
    df["product_id"]      = df["product_id"].astype(int)
    df["predicted_units"] = pd.to_numeric(df["predicted_units"], errors="coerce")
    return df


# ── Load actuals from Supabase ────────────────────────────

def load_actuals(week_start_min=None) -> pd.DataFrame:
    """
    Pull weekly actual units sold from Supabase.
    Filters to weeks >= week_start_min if provided.
    """
    where = ""
    if week_start_min is not None:
        where = f"WHERE date >= '{pd.Timestamp(week_start_min).date()}'"

    df = run_query(f"""
        SELECT
            DATE_TRUNC('week', date)::date  AS week_start,
            store_id::text                  AS store_id,
            product_id,
            SUM(units_sold)                 AS units_sold
        FROM core.fact_sales
        {where}
        GROUP BY 1, 2, 3
        ORDER BY 1
    """)

    df["week_start"] = pd.to_datetime(df["week_start"])
    df["store_id"]   = df["store_id"].astype(str)
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce").astype(int)
    df["units_sold"] = pd.to_numeric(df["units_sold"], errors="coerce")
    return df


# ── Build monitoring table ────────────────────────────────

def build_monitoring_table(forecasts: pd.DataFrame, actuals: pd.DataFrame) -> pd.DataFrame:
    df = forecasts.merge(actuals, on=["week_start", "store_id", "product_id"], how="left")
    df["abs_error"]    = (df["units_sold"] - df["predicted_units"]).abs()
    df["signed_error"] = df["predicted_units"] - df["units_sold"]
    df["ape"]          = df["abs_error"] / df["units_sold"].replace(0, np.nan)
    return df


def build_weekly_summary(df: pd.DataFrame) -> pd.DataFrame:
    weekly = df.groupby("week_start", as_index=False).agg(
        actual_sum    =("units_sold",      "sum"),
        predicted_sum =("predicted_units", "sum"),
        abs_error_sum =("abs_error",       "sum"),
        bias_sum      =("signed_error",    "sum"),
        item_count    =("product_id",      "count"),
    )
    weekly["WAPE"]     = weekly["abs_error_sum"] / weekly["actual_sum"].replace(0, np.nan)
    weekly["BIAS_PCT"] = weekly["bias_sum"]      / weekly["actual_sum"].replace(0, np.nan)
    weekly["alert"]    = weekly["WAPE"].apply(
        lambda x: "Check Model" if pd.notna(x) and x > WAPE_ALERT_THRESHOLD else "OK"
    )
    return weekly


# ── Overall metrics ───────────────────────────────────────

def print_overall_metrics(df: pd.DataFrame) -> None:
    overall_mae  = df["abs_error"].mean()
    overall_wape = df["abs_error"].sum() / df["units_sold"].sum()
    overall_bias = df["signed_error"].sum() / df["units_sold"].sum()

    print("\nOverall Monitoring Metrics")
    print("-" * 35)
    print(f"Overall MAE    : {overall_mae:.4f}")
    print(f"Overall WAPE   : {overall_wape:.4%}")
    print(f"Overall Bias % : {overall_bias:.4%}")

    alert_weeks = (df.groupby("week_start")["abs_error"].sum() /
                   df.groupby("week_start")["units_sold"].sum())
    n_alerts = (alert_weeks > WAPE_ALERT_THRESHOLD).sum()
    if n_alerts:
        print(f"\n  {n_alerts} week(s) exceeded WAPE threshold of {WAPE_ALERT_THRESHOLD:.0%} — review needed.")
    else:
        print(f"\n  All weeks within WAPE threshold ({WAPE_ALERT_THRESHOLD:.0%}).")


# ── Plots ─────────────────────────────────────────────────

def plot_wape(weekly: pd.DataFrame, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 4))
    colors = ["#C44E52" if a == "Check Model" else "#4C72B0" for a in weekly["alert"]]
    ax.bar(weekly["week_start"], weekly["WAPE"] * 100, color=colors, width=5)
    ax.axhline(WAPE_ALERT_THRESHOLD * 100, color="red", ls="--", lw=1,
               label=f"Alert threshold ({WAPE_ALERT_THRESHOLD:.0%})")
    ax.set_title("Weekly Forecast WAPE  (red = alert threshold exceeded)")
    ax.set_ylabel("WAPE (%)")
    ax.set_xlabel("Week")
    ax.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    print(f"Saved: {path}")


def plot_actual_vs_predicted(weekly: pd.DataFrame, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(weekly["week_start"], weekly["actual_sum"],    marker="o", label="Actual",    color="#4C72B0")
    ax.plot(weekly["week_start"], weekly["predicted_sum"], marker="o", label="Predicted", color="#C44E52", ls="--")
    ax.set_title("Actual vs Predicted Weekly Units Sold")
    ax.set_ylabel("Units Sold")
    ax.set_xlabel("Week")
    ax.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    print(f"Saved: {path}")


# ── Save helpers ──────────────────────────────────────────

def save_csv(df: pd.DataFrame, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Saved: {path}")


# ── Main ──────────────────────────────────────────────────

def main() -> None:
    print("Loading forecasts...")
    forecasts = load_forecasts(FORECAST_PATH)

    min_date = forecasts["week_start"].min()
    print(f"Loading actuals from Supabase (from {min_date.date()})...")
    actuals = load_actuals(week_start_min=min_date)

    print("Building monitoring table...")
    df_monitor = build_monitoring_table(forecasts, actuals)

    print("Building weekly summary...")
    weekly_summary = build_weekly_summary(df_monitor)

    print("Saving outputs...")
    save_csv(df_monitor,     OUTPUT_MONITOR_PATH)
    save_csv(weekly_summary, OUTPUT_SUMMARY_PATH)

    print("Creating plots...")
    plot_wape(weekly_summary, PLOT_WAPE_PATH)
    plot_actual_vs_predicted(weekly_summary, PLOT_ACTUAL_VS_PRED)

    print_overall_metrics(df_monitor)

    print("\nWeekly Summary:")
    print(weekly_summary.to_string(index=False))


if __name__ == "__main__":
    main()
