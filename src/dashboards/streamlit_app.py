# src/dashboards/streamlit_app.py
# --------------------------------
# SunnyBest Retail Intelligence Platform (Mode A)
# - Streamlit loads data + models locally (no API calls)
# - Clean project-root paths (works from anywhere)
# - Useful business tabs: Overview, Forecast (baseline), Stockouts (observed), Pricing (observed)

import streamlit as st
import pandas as pd
import joblib
from pathlib import Path

# =========================
# CONFIG / PATHS
# =========================
st.set_page_config(page_title="SunnyBest Analytics Platform", layout="wide")

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../retail-sales-forecasting-genai
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "sunnybest_sales.csv"
FORECAST_MODEL_PATH = PROJECT_ROOT / "models" / "xgb_revenue_forecast.pkl"
STOCKOUT_MODEL_PATH = PROJECT_ROOT / "models" / "stockout_classifier.pkl"

# =========================
# UI HEADER
# =========================
st.title("📊 SunnyBest Retail Intelligence Platform")
st.success("App loaded ✅")

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    return df

df = load_data(DATA_PATH)

# =========================
# LOAD MODELS (LOCAL)
# =========================
@st.cache_resource
def load_model(path: Path):
    return joblib.load(path)

forecast_model = load_model(FORECAST_MODEL_PATH)
stockout_model = load_model(STOCKOUT_MODEL_PATH)

# =========================
# SIDEBAR STATUS
# =========================
st.sidebar.header("System Status")
st.sidebar.write("✅ Data path:", str(DATA_PATH))
st.sidebar.write("✅ Data shape:", df.shape)
st.sidebar.write("✅ Forecast model:", FORECAST_MODEL_PATH.name)
st.sidebar.write("✅ Stockout model:", STOCKOUT_MODEL_PATH.name)

# =========================
# TABS
# =========================
tab1, tab2, tab3, tab4 = st.tabs([
    "Overview",
    "Revenue Forecast (Baseline)",
    "Stockout Risk (Observed)",
    "Pricing Explorer (Observed)"
])

# =========================
# TAB 1: OVERVIEW
# =========================
with tab1:
    st.subheader("Business Overview")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Revenue (₦)", f"{df['revenue'].sum():,.0f}")
    col2.metric("Total Units Sold", f"{df['units_sold'].sum():,.0f}")
    col3.metric("Stockout Rate", f"{df['stockout_occurred'].mean() * 100:.2f}%")

    st.write("### Revenue Trend Over Time")
    daily_rev = df.groupby("date")["revenue"].sum().sort_index()
    st.line_chart(daily_rev)

    st.write("### Top Categories by Revenue")
    cat_rev = df.groupby("category")["revenue"].sum().sort_values(ascending=False).head(10)
    st.dataframe(cat_rev.reset_index().rename(columns={"revenue": "total_revenue"}))

# =========================
# TAB 2: FORECAST (BASELINE)
# =========================
with tab2:
    st.subheader("Revenue Forecast (Baseline)")
    st.info(
        "This Mode A dashboard uses a baseline forecast to avoid feature-mismatch issues. "
        "Model-based forecasting via the API will be added during polish."
    )

    daily = df.groupby("date")["revenue"].sum().reset_index().sort_values("date")
    st.write("### Historical Revenue")
    st.line_chart(daily.set_index("date")["revenue"])

    horizon = st.slider("Forecast horizon (days)", 7, 90, 30)

    # Naive baseline: mean of last 30 days
    window = st.slider("Baseline window (days)", 7, 90, 30)
    last_mean = daily.tail(window)["revenue"].mean()

    future_dates = pd.date_range(daily["date"].max() + pd.Timedelta(days=1), periods=horizon, freq="D")
    forecast = pd.DataFrame({"date": future_dates, "forecast_revenue": last_mean})

    st.write("### Baseline Forecast (Last-window Mean)")
    st.line_chart(forecast.set_index("date")["forecast_revenue"])

    st.caption(
        "Note: Your trained XGBoost model is loaded successfully. "
        "We’ll wire full feature generation + model predictions into this tab during polish."
    )

# =========================
# TAB 3: STOCKOUT (OBSERVED)
# =========================
with tab3:
    st.subheader("Stockout Risk (Observed Patterns)")
    st.info(
        "This tab shows real stockout patterns from the dataset. "
        "Model-based predictions will be added in the polish phase."
    )

    # Stockout rate by category
    st.write("### Stockout Rate by Category")
    by_cat = (
        df.groupby("category")["stockout_occurred"]
        .mean()
        .sort_values(ascending=False)
        .mul(100)
        .round(2)
        .reset_index(name="stockout_%")
    )
    st.dataframe(by_cat, use_container_width=True)

    # Stockout rate by store
    if "store_name" in df.columns:
        st.write("### Stockout Rate by Store")
        by_store = (
            df.groupby("store_name")["stockout_occurred"]
            .mean()
            .sort_values(ascending=False)
            .mul(100)
            .round(2)
            .reset_index(name="stockout_%")
        )
        st.dataframe(by_store, use_container_width=True)

    # Simple filters
    st.write("### Filter and Inspect High-Risk Rows")
    cat = st.selectbox("Category", ["All"] + sorted(df["category"].dropna().unique().tolist()))
    store = st.selectbox(
        "Store",
        ["All"] + (sorted(df["store_name"].dropna().unique().tolist()) if "store_name" in df.columns else [])
    )

    filtered = df.copy()
    if cat != "All":
        filtered = filtered[filtered["category"] == cat]
    if store != "All" and "store_name" in filtered.columns:
        filtered = filtered[filtered["store_name"] == store]

    high_risk = filtered.sort_values("stockout_occurred", ascending=False).head(200)
    st.dataframe(high_risk, use_container_width=True)

# =========================
# TAB 4: PRICING (OBSERVED)
# =========================
with tab4:
    st.subheader("Pricing Explorer (Observed Data)")
    st.info(
        "This tab explores how revenue behaves across observed price points. "
        "Pricing optimisation + elasticity models are in notebooks and will be integrated during polish."
    )

    categories = sorted(df["category"].dropna().unique().tolist())
    cat = st.selectbox("Select category", categories)

    temp = df[df["category"] == cat].copy()
    temp = temp.dropna(subset=["price", "revenue"])

    st.write("### Revenue vs Price (Sample)")
    n = min(3000, len(temp))
    if n > 0:
        sample = temp[["price", "revenue"]].sample(n=n, random_state=42)
        st.scatter_chart(sample, x="price", y="revenue")
    else:
        st.warning("No rows available for this category.")

    st.write("### Price Summary")
    st.dataframe(
        temp["price"].describe().round(2).to_frame(name="price_stats"),
        use_container_width=True
    )

    st.write("### Revenue Summary")
    st.dataframe(
        temp["revenue"].describe().round(2).to_frame(name="revenue_stats"),
        use_container_width=True
    )