import os
import requests
import streamlit as st
import pandas as pd

# -----------------------------
# Config
# -----------------------------
st.set_page_config(page_title="SunnyBest Analytics Platform", layout="wide")

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


# -----------------------------
# Helpers
# -----------------------------
def api_get(path: str, params: dict | None = None):
    url = f"{API_BASE_URL}{path}"
    return requests.get(url, params=params, timeout=10)

def api_post(path: str, json: dict):
    url = f"{API_BASE_URL}{path}"
    return requests.post(url, json=json, timeout=20)


# -----------------------------
# Header + API Health
# -----------------------------
st.title("📊 SunnyBest Retail Intelligence Platform")

colA, colB = st.columns([2, 1])
with colA:
    st.write("Frontend (Streamlit) calling backend (FastAPI).")
with colB:
    st.caption(f"API_BASE_URL: `{API_BASE_URL}`")

# Health check
try:
    r = api_get("/health")
    if r.status_code == 200 and r.json().get("status") == "ok":
        st.success("API connected ✅")
    else:
        st.warning(f"API reachable but health not OK: {r.status_code} | {r.text}")
except Exception as e:
    st.error(f"API not reachable: {e}")
    st.stop()


# -----------------------------
# Tabs
# -----------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "Overview",
    "Predict (Revenue + Stockout)",
    "Predict Example (From Data)",
    "GenAI Ask (Copilot)"
])


# -----------------------------
# TAB 1: OVERVIEW (lightweight)
# -----------------------------
with tab1:
    st.subheader("Business Overview (API-ready)")
    st.info(
        "This tab can later call an API endpoint like /kpis or /timeseries. "
        "For now, it's just confirming your full system wiring is working."
    )

    st.markdown("""
**What this system can do now:**
- Predict revenue and stockout probability via `POST /predict`
- Run a prediction from a real historical row via `GET /predict/example`
- Answer questions via the experimental GenAI layer `POST /ask`
""")


# -----------------------------
# TAB 2: PREDICT (POST /predict)
# -----------------------------
with tab2:
    st.subheader("Revenue Forecast + Stockout Probability")
    st.caption("Calls: `POST /predict`")

    with st.form("predict_form"):
        c1, c2, c3 = st.columns(3)

        with c1:
            price = st.number_input("Price (₦)", min_value=0.0, value=250000.0, step=1000.0)
            regular_price = st.number_input("Regular Price (₦)", min_value=0.0, value=300000.0, step=1000.0)
            discount_pct = st.number_input("Discount %", min_value=0.0, max_value=100.0, value=15.0, step=1.0)
            promo_flag = st.selectbox("Promo Flag", [0, 1], index=1)

        with c2:
            month = st.slider("Month", 1, 12, 12)
            is_weekend = st.selectbox("Is Weekend?", [0, 1], index=1)
            is_holiday = st.selectbox("Is Holiday?", [0, 1], index=0)
            is_payday = st.selectbox("Is Payday?", [0, 1], index=1)

        with c3:
            category = st.text_input("Category", value="Mobile Phones")
            store_size = st.selectbox("Store Size", ["Small", "Medium", "Large"], index=2)
            temperature_c = st.number_input("Temperature (°C)", value=29.5, step=0.1)
            rainfall_mm = st.number_input("Rainfall (mm)", value=2.0, step=0.1)
            starting_inventory = st.number_input("Starting Inventory", min_value=0, value=12, step=1)

        submitted = st.form_submit_button("Run Prediction")

    if submitted:
        payload = {
            "price": float(price),
            "regular_price": float(regular_price),
            "discount_pct": float(discount_pct),
            "promo_flag": int(promo_flag),
            "month": int(month),
            "is_weekend": int(is_weekend),
            "is_holiday": int(is_holiday),
            "is_payday": int(is_payday),
            "category": category,
            "store_size": store_size,
            "temperature_c": float(temperature_c),
            "rainfall_mm": float(rainfall_mm),
            "starting_inventory": int(starting_inventory),
        }

        st.code(payload, language="json")

        try:
            res = api_post("/predict", payload)
            if res.status_code == 200:
                out = res.json()
                m1, m2 = st.columns(2)
                m1.metric("Predicted Revenue (₦)", f"{out['predicted_revenue']:,.2f}")
                m2.metric("Stockout Probability", f"{out['stockout_probability']:.3f}")
                st.success("Prediction successful ✅")
            else:
                st.error(f"API error {res.status_code}: {res.text}")
        except Exception as e:
            st.error(f"Request failed: {e}")


# -----------------------------
# TAB 3: PREDICT EXAMPLE (GET /predict/example)
# -----------------------------
with tab3:
    st.subheader("Predict Using a Real Historical Row")
    st.caption("Calls: `GET /predict/example`")

    c1, c2, c3 = st.columns(3)
    with c1:
        date = st.text_input("date (YYYY-MM-DD) optional", value="")
    with c2:
        store_id = st.text_input("store_id optional", value="")
    with c3:
        product_id = st.text_input("product_id optional", value="")

    params = {}
    if date.strip():
        params["date"] = date.strip()
    if store_id.strip():
        params["store_id"] = int(store_id.strip())
    if product_id.strip():
        params["product_id"] = int(product_id.strip())

    if st.button("Run Example Prediction"):
        try:
            res = api_get("/predict/example", params=params if params else None)
            if res.status_code == 200:
                out = res.json()
                st.success("Example prediction returned ✅")
                st.json(out)
            else:
                st.error(f"API error {res.status_code}: {res.text}")
        except Exception as e:
            st.error(f"Request failed: {e}")


# -----------------------------
# TAB 4: GENAI ASK (POST /ask)
# -----------------------------
with tab4:
    st.subheader("GenAI Copilot (Experimental)")
    st.caption("Calls: `POST /ask`")

    query = st.text_input("Ask a question", value="Summarise stockout drivers and what SunnyBest should do.")
    attach_payload = st.checkbox("Attach the same payload used in /predict? (optional)", value=False)

    st.info("This is your early GenAI layer: RAG-like retrieval over DOCS + a router tool (run_copilot).")

    if st.button("Ask Copilot"):
        req = {"query": query}
        if attach_payload:
            # reuse a minimal payload example if user didn't run predict
            req["payload"] = {
                "category": "Mobile Phones",
                "store_size": "Large",
                "month": 12,
                "promo_flag": 1,
                "discount_pct": 15,
                "starting_inventory": 12,
            }

        try:
            res = api_post("/ask", req)
            if res.status_code == 200:
                out = res.json()
                st.success("Copilot response ✅")
                # If run_copilot returns a string:
                if isinstance(out, str):
                    st.write(out)
                else:
                    st.json(out)
            else:
                st.error(f"API error {res.status_code}: {res.text}")
        except Exception as e:
            st.error(f"Request failed: {e}")