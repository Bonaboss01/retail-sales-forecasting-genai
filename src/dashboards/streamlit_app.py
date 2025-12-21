import streamlit as st
import pandas as pd
import joblib



st.set_page_config(
    page_title="SunnyBest Analytics Platform",
    layout="wide"
)

st.title("📊 SunnyBest Retail Intelligence Platform")
st.success("App loaded ✅")
st.write("Starting up...")


# Load data
@st.cache_data
def load_data():
    return pd.read_csv("data/raw/sunnybest_sales.csv", parse_dates=["date"])

df = load_data()

# Load models
forecast_model = joblib.load("models/xgb_revenue_forecast.pkl")
stockout_model = joblib.load("models/stockout_classifier.pkl")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "Overview",
    "Demand Forecast",
    "Stockout Risk",
    "Pricing Simulator"
])

# -------------------------
# TAB 1: OVERVIEW
# -------------------------
with tab1:
    st.subheader("Business Overview")

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Revenue (₦)", f"{df['revenue'].sum():,.0f}")
    col2.metric("Total Units Sold", f"{df['units_sold'].sum():,.0f}")
    col3.metric("Stockout Rate", f"{df['stockout_occurred'].mean()*100:.2f}%")

    st.line_chart(
        df.groupby("date")["revenue"].sum()
    )

# -------------------------
# TAB 2: DEMAND FORECAST
# -------------------------
with tab2:
    st.subheader("Revenue Forecast")

    st.info("This uses the trained XGBoost forecasting model.")

    st.write("Forecast logic already validated in notebooks.")

# -------------------------
# TAB 3: STOCKOUT RISK
# -------------------------
with tab3:
    st.subheader("Stockout Risk Prediction")

    st.info("High-risk products and stores can be flagged here.")

# -------------------------
# TAB 4: PRICING
# -------------------------
with tab4:
    st.subheader("Pricing What-If Simulator")

    price = st.slider("Price (₦)", 10000, 500000, 250000, step=5000)
    st.write(f"Selected price: ₦{price:,.0f}")
