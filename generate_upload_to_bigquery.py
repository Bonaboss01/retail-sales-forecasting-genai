# generate_upload_to_bigquery.py
#
# Version 2 of the SunnyBest data generator — writes to BigQuery instead of Supabase.
# All data generation logic is identical to generate_upload_to_supabase.py.
# Only the connection and upload layer has changed.
#
# Usage:
#   python3 generate_upload_to_bigquery.py
#   python3 generate_upload_to_bigquery.py 2026-01-01 2026-06-08
#
# Requirements:
#   pip install google-cloud-bigquery pyarrow
#   gcloud auth application-default login

import sys
import os
import pickle
from pathlib import Path
from datetime import datetime
from uuid import uuid4

import numpy as np
import pandas as pd
from google.cloud import bigquery
from google.api_core.exceptions import NotFound


# =========================================================
# CONFIG
# =========================================================

PROJECT_ID = "sfs-dev-498722"
DATASET_ID = "sunnybest"
LOCATION   = "europe-west2"   # London

SEED       = 42
SCALE_MODE = os.getenv("SCALE_MODE", "small").lower()
RESET_DB   = os.getenv("RESET_DB", "false").lower() == "true"

print(f"Running SunnyBest BigQuery generator — SCALE_MODE={SCALE_MODE}")

DEFAULT_START_DATE = "2021-01-01"
DEFAULT_END_DATE   = datetime.today().strftime("%Y-%m-%d")

if len(sys.argv) >= 3:
    USER_START_DATE = sys.argv[1]
    USER_END_DATE   = sys.argv[2]
    print(f"Date range (custom) : {USER_START_DATE} → {USER_END_DATE}")
else:
    USER_START_DATE = DEFAULT_START_DATE
    USER_END_DATE   = DEFAULT_END_DATE
    print(f"Date range (default): {USER_START_DATE} → {USER_END_DATE}")

N_PRODUCTS    = 200
N_STORES_EXTRA = 0

STATE_DIR  = "data/state/"
STATE_FILE = "sunnybest_bq_generator_state.pkl"   # separate from Supabase state

if SCALE_MODE == "large":
    if len(sys.argv) < 3:
        USER_START_DATE = "2018-01-01"
        USER_END_DATE   = datetime.today().strftime("%Y-%m-%d")
    N_PRODUCTS     = 800
    N_STORES_EXTRA = 43


# =========================================================
# BIGQUERY CLIENT
# =========================================================

client = bigquery.Client(project=PROJECT_ID)

UNIQUE_KEYS = {
    "dim_calendar":            ["date"],
    "dim_stores":              ["store_id"],
    "dim_products":            ["product_id"],
    "dim_store_products":      ["store_id", "product_id"],
    "dim_policy_regimes":      ["policy_id"],
    "fact_weather":            ["date", "city"],
    "fact_promotions":         ["date", "store_id", "product_id"],
    "fact_sales":              ["date", "store_id", "product_id"],
    "fact_inventory":          ["date", "store_id", "product_id"],
    "fact_customer_activity":  ["date", "store_id"],
    "fact_store_operations":   ["date", "store_id"],
    "fact_restriction_events": ["date", "store_id", "product_id", "restriction_type"],
}


# =========================================================
# STATE HELPERS  (identical to Supabase version)
# =========================================================

def get_state_path(state_dir=STATE_DIR, state_file=STATE_FILE):
    path = Path(state_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path / state_file


def load_generator_state():
    state_path = get_state_path()
    if not state_path.exists():
        return None
    with open(state_path, "rb") as f:
        state = pickle.load(f)
    print(f"Loaded generator state from: {state_path}")
    return state


def save_generator_state(state: dict):
    state_path = get_state_path()
    with open(state_path, "wb") as f:
        pickle.dump(state, f)
    print(f"Saved generator state to: {state_path}")


def initialize_rng(prior_state):
    if prior_state and "rng_state" in prior_state:
        np.random.set_state(prior_state["rng_state"])
        print("Restored numpy RNG state from prior run.")
    else:
        np.random.seed(SEED)
        print(f"Initialized numpy RNG with seed={SEED}.")


def get_effective_forward_window(user_start_date, user_end_date, prior_state):
    requested_start = pd.to_datetime(user_start_date)
    requested_end   = pd.to_datetime(user_end_date)

    if requested_end < requested_start:
        raise ValueError("END_DATE cannot be earlier than START_DATE.")

    if prior_state and prior_state.get("last_generated_date") is not None:
        last_generated_date = pd.to_datetime(prior_state["last_generated_date"])
        forward_start = max(requested_start, last_generated_date + pd.Timedelta(days=1))
    else:
        last_generated_date = None
        forward_start = requested_start

    if forward_start > requested_end:
        return last_generated_date, None, requested_end

    return last_generated_date, forward_start, requested_end


def parse_key(k):
    if isinstance(k, tuple):
        return k
    if isinstance(k, str):
        parts = k.strip("()").split(",")
        if len(parts) == 2:
            return int(parts[0]), int(parts[1])
    return k


def weighted_choice(options, probs):
    return np.random.choice(options, p=probs)


# =========================================================
# BIGQUERY HELPERS
# =========================================================

def ensure_dataset():
    dataset_ref = bigquery.Dataset(f"{PROJECT_ID}.{DATASET_ID}")
    dataset_ref.location = LOCATION
    client.create_dataset(dataset_ref, exists_ok=True)
    print(f"Dataset ready: {PROJECT_ID}.{DATASET_ID}  (location: {LOCATION})")


def table_exists(table_name: str) -> bool:
    try:
        client.get_table(f"{PROJECT_ID}.{DATASET_ID}.{table_name}")
        return True
    except NotFound:
        return False


def table_has_rows(table_name: str) -> bool:
    if not table_exists(table_name):
        return False
    try:
        result = client.query(
            f"SELECT COUNT(*) AS n FROM `{PROJECT_ID}.{DATASET_ID}.{table_name}`"
        ).result()
        return list(result)[0].n > 0
    except Exception:
        return False


def load_table(table_name: str) -> pd.DataFrame:
    return client.query(
        f"SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.{table_name}`"
    ).to_dataframe()


def reset_bigquery_tables():
    print("RESET_DB=true — dropping all SunnyBest BigQuery tables...")
    tables = [
        "fact_sales", "fact_inventory", "fact_customer_activity",
        "fact_store_operations", "fact_promotions", "fact_weather",
        "fact_restriction_events", "dim_calendar", "dim_policy_regimes",
        "dim_store_products", "dim_products", "dim_stores",
    ]
    for t in tables:
        client.delete_table(f"{PROJECT_ID}.{DATASET_ID}.{t}", not_found_ok=True)
        print(f"  Dropped: {t}")

    state_path = get_state_path()
    if state_path.exists():
        state_path.unlink()
        print(f"Deleted local state: {state_path}")
    print("Reset complete.")


def upload_to_bigquery(df: pd.DataFrame, table_name: str, batch_size: int = 50000):
    """
    Safe incremental upload to BigQuery:
    - Loads data in batches to a temporary staging table
    - On first load: copies staging to main table directly
    - On subsequent loads: MERGEs staging into main (no duplicates)
    - Drops the staging table after each batch
    """
    if df is None or df.empty:
        print(f"  No rows for {table_name} — skipping.")
        return

    df = df.copy()

    # Force these columns to string type, even if all values are None.
    # Without this, BigQuery's schema auto-detection can incorrectly infer
    # INT64 for columns that are entirely null in a given batch, causing
    # a type mismatch when merging into the main table.
    for col in ["promo_type", "restriction_type", "restriction_reason", "restriction_severity"]:
        if col in df.columns:
            df[col] = df[col].astype("string")

    # Convert date columns to plain date objects (BigQuery DATE type)
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.date

    table_id = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"
    keys     = UNIQUE_KEYS.get(table_name, [])
    total    = len(df)

    print(f"Uploading {total:,} rows → {table_id}")

    for start in range(0, total, batch_size):
        end   = min(start + batch_size, total)
        batch = df.iloc[start:end].copy()
        temp_id = f"{PROJECT_ID}.{DATASET_ID}.tmp_{table_name}_{uuid4().hex[:8]}"

        # ── Load batch to staging table ────────────────────────────────────────
        job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
        job = client.load_table_from_dataframe(batch, temp_id, job_config=job_config)
        job.result()

        # ── Merge or copy into main table ──────────────────────────────────────
        if not table_exists(table_name) or not keys:
            # First load — copy staging directly to main
            copy_job = client.copy_table(temp_id, table_id)
            copy_job.result()
        else:
            cols           = list(batch.columns)
            merge_on       = " AND ".join([f"T.`{k}` = S.`{k}`" for k in keys])
            insert_cols    = ", ".join([f"`{c}`" for c in cols])
            insert_vals    = ", ".join([f"S.`{c}`" for c in cols])

            merge_sql = f"""
                MERGE `{table_id}` T
                USING `{temp_id}` S
                ON {merge_on}
                WHEN NOT MATCHED THEN
                    INSERT ({insert_cols}) VALUES ({insert_vals})
            """
            client.query(merge_sql).result()

        # ── Drop staging table ─────────────────────────────────────────────────
        client.delete_table(temp_id, not_found_ok=True)

        print(f"  Rows {start + 1:,} – {end:,} of {total:,} done")

    print(f"Done: {table_name}")


def load_or_create_dim(table_name: str, generator_func):
    if table_has_rows(table_name):
        df = load_table(table_name)
        print(f"Loaded {table_name} from BigQuery ({len(df):,} rows)")
        return df
    print(f"{table_name} is empty — generating once.")
    df = generator_func()
    upload_to_bigquery(df, table_name)
    return df


def load_policy_regimes(calendar_df: pd.DataFrame):
    if not table_has_rows("dim_policy_regimes"):
        print("No policy regimes found — generating initial policies.")
        initial = generate_policy_regimes(calendar_df)
        upload_to_bigquery(initial, "dim_policy_regimes")
        return initial

    existing = load_table("dim_policy_regimes")
    existing["start_date"] = pd.to_datetime(existing["start_date"], format="mixed")
    existing["end_date"]   = pd.to_datetime(existing["end_date"],   format="mixed")

    window_start = pd.to_datetime(calendar_df["date"].min())
    window_end   = pd.to_datetime(calendar_df["date"].max())

    active = existing[
        (existing["start_date"] <= window_end) &
        (existing["end_date"]   >= window_start)
    ].copy()

    print(f"Loaded {len(active):,} active policy regimes for this window.")
    return active


# =========================================================
# 1. STORES
# =========================================================

def generate_stores(n_extra: int = 0) -> pd.DataFrame:
    stores_list = [
        {"store_id": 1, "store_name": "SunnyBest Benin Main",  "city": "Benin",     "area": "Oredo",       "region": "Edo South",   "store_type": "Mall",        "store_size": "Large"},
        {"store_id": 2, "store_name": "SunnyBest Ekpoma",      "city": "Ekpoma",    "area": "Esan West",   "region": "Edo Central", "store_type": "High Street", "store_size": "Medium"},
        {"store_id": 3, "store_name": "SunnyBest Auchi",       "city": "Auchi",     "area": "Etsako West", "region": "Edo North",   "store_type": "High Street", "store_size": "Medium"},
        {"store_id": 4, "store_name": "SunnyBest Irrua",       "city": "Irrua",     "area": "Esan Central","region": "Edo Central", "store_type": "Plaza",       "store_size": "Small"},
        {"store_id": 5, "store_name": "SunnyBest Igueben",     "city": "Igueben",   "area": "Igueben",     "region": "Edo Central", "store_type": "High Street", "store_size": "Small"},
        {"store_id": 6, "store_name": "SunnyBest Agenebode",   "city": "Agenebode", "area": "Etsako East", "region": "Edo North",   "store_type": "Plaza",       "store_size": "Small"},
        {"store_id": 7, "store_name": "SunnyBest Ogwa",        "city": "Ogwa",      "area": "Esan West",   "region": "Edo Central", "store_type": "High Street", "store_size": "Small"},
    ]
    base = pd.DataFrame(stores_list)
    if n_extra <= 0:
        return base

    cities      = base["city"].unique().tolist()
    store_types = base["store_type"].unique().tolist()
    store_sizes = base["store_size"].unique().tolist()
    regions     = base["region"].unique().tolist()
    areas       = base["area"].unique().tolist()
    start_id    = int(base["store_id"].max()) + 1

    extra_rows = []
    for i in range(n_extra):
        sid  = start_id + i
        city = np.random.choice(cities)
        extra_rows.append({
            "store_id":   sid,
            "store_name": f"SunnyBest {city} Branch {sid}",
            "city":       city,
            "area":       np.random.choice(areas),
            "region":     np.random.choice(regions),
            "store_type": np.random.choice(store_types),
            "store_size": np.random.choice(store_sizes),
        })
    return pd.concat([base, pd.DataFrame(extra_rows)], ignore_index=True)


# =========================================================
# 2. PRODUCTS
# =========================================================

CATEGORIES = {
    "Mobile Phones":       ["Samsung", "Apple", "Tecno", "Infinix", "Itel"],
    "Laptops & Computers": ["HP", "Dell", "Lenovo", "Acer", "Asus"],
    "Televisions":         ["LG", "Samsung", "Hisense", "Sony"],
    "Refrigerators":       ["LG", "Hisense", "Haier Thermocool"],
    "Air Conditioners":    ["LG", "Hisense", "Panasonic"],
    "Small Appliances":    ["Binatone", "Philips", "Century"],
    "Network Devices":     ["Huawei", "ZTE", "TP-Link"],
    "Accessories":         ["Oraimo", "Anker", "Generic"],
    "Telecom Services":    ["MTN", "Glo", "Airtel", "9mobile"],
}

CATEGORY_WEIGHTS = {
    "Mobile Phones": 0.20, "Laptops & Computers": 0.15, "Televisions": 0.10,
    "Refrigerators": 0.08, "Air Conditioners": 0.07,    "Small Appliances": 0.15,
    "Network Devices": 0.10, "Accessories": 0.10,       "Telecom Services": 0.05,
}


def generate_products(n_products: int) -> pd.DataFrame:
    rows       = []
    product_id = 1001
    cat_list   = list(CATEGORY_WEIGHTS.keys())
    weights    = list(CATEGORY_WEIGHTS.values())

    for _ in range(n_products):
        cat   = np.random.choice(cat_list, p=weights)
        brand = np.random.choice(CATEGORIES[cat])

        if cat == "Mobile Phones":              regular_price = np.random.randint(40000,  250000)
        elif cat == "Laptops & Computers":      regular_price = np.random.randint(120000, 450000)
        elif cat == "Televisions":              regular_price = np.random.randint(60000,  300000)
        elif cat in ["Refrigerators",
                     "Air Conditioners"]:       regular_price = np.random.randint(90000,  350000)
        elif cat == "Small Appliances":         regular_price = np.random.randint(8000,   45000)
        elif cat == "Network Devices":          regular_price = np.random.randint(10000,  70000)
        elif cat == "Accessories":              regular_price = np.random.randint(2000,   20000)
        elif cat == "Telecom Services":         regular_price = np.random.randint(500,    10000)
        else:                                   regular_price = np.random.randint(10000,  200000)

        rows.append({
            "product_id":      product_id,
            "product_name":    f"{brand} {cat.split()[0]} Model-{np.random.randint(100, 999)}",
            "category":        cat,
            "brand":           brand,
            "regular_price":   regular_price,
            "cost_price":      int(regular_price * np.random.uniform(0.6, 0.8)),
            "is_seasonal":     int(cat in ["Air Conditioners", "Refrigerators", "Televisions",
                                           "Mobile Phones", "Telecom Services"]),
            "warranty_months": np.random.choice([6, 12, 24]),
        })
        product_id += 1

    return pd.DataFrame(rows)


# =========================================================
# 2b. STORE-PRODUCT ASSORTMENT
# =========================================================

EXCLUDED_FROM_SMALL  = {"Air Conditioners", "Refrigerators", "Laptops & Computers", "Televisions"}
EXCLUDED_FROM_MEDIUM = {"Air Conditioners", "Refrigerators"}


def generate_store_product_assortment(stores_df: pd.DataFrame, products_df: pd.DataFrame) -> pd.DataFrame:
    """
    Each store only carries a subset of products.
    Large=100%, Medium=72% (no big appliances), Small=45% (no big appliances or TVs).
    """
    coverage = {"Large": 1.0, "Medium": 0.72, "Small": 0.45}
    rows = []
    for _, store in stores_df.iterrows():
        size = store["store_size"]
        for _, product in products_df.iterrows():
            if size == "Small"  and product["category"] in EXCLUDED_FROM_SMALL:
                continue
            if size == "Medium" and product["category"] in EXCLUDED_FROM_MEDIUM:
                continue
            if np.random.rand() < coverage[size]:
                rows.append({"store_id": int(store["store_id"]), "product_id": int(product["product_id"])})
    return pd.DataFrame(rows)


# =========================================================
# 3. CALENDAR / WEATHER / PROMOTIONS / POLICIES
# =========================================================

def generate_calendar(start_date: str, end_date: str) -> pd.DataFrame:
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    cal   = pd.DataFrame({"date": dates})
    cal["year"]          = cal["date"].dt.year
    cal["month"]         = cal["date"].dt.month
    cal["day"]           = cal["date"].dt.day
    cal["day_of_week"]   = cal["date"].dt.day_name()
    cal["day_of_week_num"] = cal["date"].dt.weekday
    cal["week_of_year"]  = cal["date"].dt.isocalendar().week.astype(int)
    cal["is_weekend"]    = cal["day_of_week"].isin(["Saturday", "Sunday"])

    fixed_holidays = {"01-01", "05-01", "10-01", "12-25", "12-26"}
    cal["is_holiday"] = cal["date"].apply(lambda d: d.strftime("%m-%d") in fixed_holidays)
    cal["is_payday"]  = cal["day"] == 25

    def season(m):
        if m in [11, 12, 1, 2]:   return "Dry"
        if m in [3, 4, 5, 6, 7]:  return "Early Rainy"
        return "Late Rainy"

    cal["season"]                = cal["month"].apply(season)
    cal["is_black_friday_period"] = (cal["month"] == 11) & (cal["day_of_week"] == "Friday")
    return cal


def generate_weather(calendar_df: pd.DataFrame, stores_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, store in stores_df.iterrows():
        city = store["city"]
        for _, day in calendar_df.iterrows():
            month      = day["month"]
            base_temp  = 30 if month in [1,2,3] else 29 if month in [4,5,6] else 27 if month in [7,8,9] else 28
            temperature = base_temp + np.random.normal(0, 1.5)
            rainfall    = max(0, np.random.normal(5, 5)) if month in [4,5,6,7,8,9] else max(0, np.random.normal(1, 2))
            condition   = "Sunny" if rainfall == 0 else "Cloudy" if rainfall < 3 else "Rainy"
            rows.append({
                "date": day["date"], "city": city,
                "temperature_c": round(temperature, 1),
                "rainfall_mm":   round(rainfall, 1),
                "weather_condition": condition,
            })
    return pd.DataFrame(rows)


def generate_promotions(calendar_df, stores_df, products_df):
    rows = []
    for _, day in calendar_df.iterrows():
        prob = 0.01
        if day["is_weekend"]:            prob += 0.02
        if day["is_holiday"]:            prob += 0.05
        if day["is_black_friday_period"]: prob += 0.10
        if day["month"] == 12:           prob += 0.04

        if np.random.rand() < prob:
            n       = np.random.randint(3, 15)
            sids    = np.random.choice(stores_df["store_id"],   size=n, replace=True)
            pids    = np.random.choice(products_df["product_id"], size=n, replace=True)
            for sid, pid in zip(sids, pids):
                promo_type   = np.random.choice(["Discount","Bundle","Free Accessory","Price Slash"], p=[0.6,0.15,0.15,0.10])
                discount_pct = np.random.choice([5,10,15,20,25,30]) if promo_type in ["Discount","Price Slash"] else 0
                rows.append({"date": day["date"], "store_id": int(sid), "product_id": int(pid),
                             "promo_type": promo_type, "discount_pct": discount_pct, "promo_flag": 1})

    if not rows:
        return pd.DataFrame(columns=["date","store_id","product_id","promo_type","discount_pct","promo_flag"])
    return pd.DataFrame(rows).drop_duplicates(subset=["date","store_id","product_id"]).reset_index(drop=True)


def generate_policy_regimes(calendar_df):
    min_date = calendar_df["date"].min()
    max_date = calendar_df["date"].max()
    candidates = [
        {"policy_name":"Telecom Seasonal Push","affected_category":"Telecom Services","affected_store_type":None,"demand_multiplier":1.15,"discount_cap_pct":20,"replenishment_multiplier":1.10,"service_intensity_multiplier":1.08},
        {"policy_name":"Premium Electronics Margin Protection","affected_category":"Mobile Phones","affected_store_type":None,"demand_multiplier":0.96,"discount_cap_pct":10,"replenishment_multiplier":0.95,"service_intensity_multiplier":1.02},
        {"policy_name":"Mall Expansion Drive","affected_category":None,"affected_store_type":"Mall","demand_multiplier":1.08,"discount_cap_pct":25,"replenishment_multiplier":1.12,"service_intensity_multiplier":1.10},
        {"policy_name":"Small Store Inventory Control","affected_category":None,"affected_store_type":"Plaza","demand_multiplier":0.98,"discount_cap_pct":15,"replenishment_multiplier":0.88,"service_intensity_multiplier":1.00},
        {"policy_name":"Cooling Appliances Availability Programme","affected_category":"Air Conditioners","affected_store_type":None,"demand_multiplier":1.10,"discount_cap_pct":20,"replenishment_multiplier":1.20,"service_intensity_multiplier":1.05},
    ]
    selected   = np.random.choice(len(candidates), size=min(4, len(candidates)), replace=False)
    total_days = max(1, (max_date - min_date).days)
    windows    = []
    for i, idx in enumerate(selected, start=1):
        p          = candidates[idx]
        start_off  = np.random.randint(0, max(1, total_days))
        duration   = np.random.randint(90, 240)
        start_date = min_date + pd.Timedelta(days=int(start_off))
        end_date   = min(start_date + pd.Timedelta(days=int(duration)), max_date)
        windows.append({"policy_id": i, "start_date": start_date, "end_date": end_date, **p})
    return pd.DataFrame(windows)


# =========================================================
# 4. DEMAND / INVENTORY HELPERS
# =========================================================

def base_demand_for_category(category):
    if category == "Mobile Phones":          return np.random.uniform(0.5, 3.0)
    if category == "Laptops & Computers":    return np.random.uniform(0.2, 1.0)
    if category == "Televisions":            return np.random.uniform(0.1, 0.8)
    if category in ["Refrigerators",
                    "Air Conditioners"]:     return np.random.uniform(0.05, 0.5)
    if category == "Small Appliances":       return np.random.uniform(0.5, 4.0)
    if category == "Network Devices":        return np.random.uniform(0.2, 2.0)
    if category == "Accessories":            return np.random.uniform(1.0, 8.0)
    if category == "Telecom Services":       return np.random.uniform(5.0, 30.0)
    return np.random.uniform(0.5, 3.0)

def target_inventory_days(category):
    if category in ["Mobile Phones","Network Devices","Accessories","Telecom Services"]: return 4, 10
    if category in ["Laptops & Computers","Televisions"]:                                return 6, 14
    if category in ["Refrigerators","Air Conditioners"]:                                 return 7, 16
    return 5, 12

def base_stockout_probability(category):
    if category in ["Mobile Phones","Network Devices","Accessories","Telecom Services"]: return 0.08
    if category in ["Laptops & Computers","Televisions"]:                                return 0.05
    return 0.03

def restock_frequency_days(store_size):
    if store_size == "Large":  return 3
    if store_size == "Medium": return 5
    return 7


# =========================================================
# 5. SALES / INVENTORY / RESTRICTIONS
# =========================================================

def sales_inventory_and_restrictions_forward(calendar_df, stores_df, products_df,
                                              weather_df, promotions_df,
                                              policy_regimes_df, store_products_df,
                                              prior_state=None):
    rows_sales, rows_inventory, rows_restrictions = [], [], []

    weather_lookup = {
        (pd.to_datetime(r.date), r.city): (r.temperature_c, r.rainfall_mm, r.weather_condition)
        for r in weather_df.itertuples(index=False)
    }
    promo_lookup = {
        (pd.to_datetime(r.date), r.store_id, r.product_id):
        {"promo_type": r.promo_type, "discount_pct": r.discount_pct, "promo_flag": r.promo_flag}
        for r in promotions_df.itertuples(index=False)
    }

    if prior_state is None:
        inventory_state, base_demand_map, last_restock_date, active_restrictions = {}, {}, {}, {}
        weekly_store_multipliers = {}
        print("No prior state — initializing from scratch.")
    else:
        inventory_state          = {parse_key(k): v for k, v in prior_state.get("inventory_state", {}).items()}
        base_demand_map          = {parse_key(k): v for k, v in prior_state.get("base_demand_map", {}).items()}
        last_restock_date        = {parse_key(k): pd.to_datetime(v) for k, v in prior_state.get("last_restock_date", {}).items()}
        active_restrictions      = {parse_key(k): v for k, v in prior_state.get("active_restrictions", {}).items()}
        weekly_store_multipliers = prior_state.get("weekly_store_multipliers", {})
        for _, v in active_restrictions.items():
            v["start_date"] = pd.to_datetime(v["start_date"])
            v["end_date"]   = pd.to_datetime(v["end_date"])
        print("Continuing from prior saved state.")

    assortment = store_products_df.groupby("store_id")["product_id"].apply(set).to_dict()

    for store in stores_df.itertuples(index=False):
        store_assortment = assortment.get(store.store_id, set())
        for product in products_df.itertuples(index=False):
            if product.product_id not in store_assortment:
                continue
            key = (store.store_id, product.product_id)
            if key not in base_demand_map:
                base_demand_map[key] = base_demand_for_category(product.category)
            if key not in inventory_state:
                lo, hi = target_inventory_days(product.category)
                inventory_state[key] = max(1, int(round(base_demand_map[key] * np.random.randint(lo, hi+1))))
            if key not in last_restock_date:
                last_restock_date[key] = pd.to_datetime(calendar_df["date"].min()) - pd.Timedelta(days=np.random.randint(1, 7))

    for current_date in sorted(pd.to_datetime(calendar_df["date"]).tolist()):
        day       = calendar_df.loc[pd.to_datetime(calendar_df["date"]) == current_date].iloc[0]
        month     = int(day["month"])
        is_weekend = bool(day["is_weekend"])
        is_holiday = bool(day["is_holiday"])
        season    = day["season"]

        for ek in [k for k, v in active_restrictions.items() if current_date > pd.to_datetime(v["end_date"])]:
            del active_restrictions[ek]

        active_policies_today = (
            pd.DataFrame() if (policy_regimes_df is None or policy_regimes_df.empty)
            else policy_regimes_df[
                (pd.to_datetime(policy_regimes_df["start_date"]) <= current_date) &
                (pd.to_datetime(policy_regimes_df["end_date"])   >= current_date)
            ]
        )

        for store in stores_df.itertuples(index=False):
            store_id, city, store_size, store_type = store.store_id, store.city, store.store_size, store.store_type
            temp, rainfall, _ = weather_lookup.get((current_date, city), (28.0, 2.0, "Cloudy"))
            store_assortment = assortment.get(store_id, set())

            week_key = (store_id, int(current_date.isocalendar()[0]), int(current_date.isocalendar()[1]))
            if week_key not in weekly_store_multipliers:
                weekly_store_multipliers[week_key] = float(np.random.choice(
                    [0.55, 0.70, 0.85, 1.00, 1.15, 1.30, 1.50],
                    p=[0.05, 0.10, 0.18, 0.30, 0.20, 0.12, 0.05]
                ))

            for product in products_df.itertuples(index=False):
                if product.product_id not in store_assortment:
                    continue
                product_id, category, regular_price = product.product_id, product.category, product.regular_price
                sp_key            = (store_id, product_id)
                current_inventory = inventory_state[sp_key]

                days_since_restock        = (current_date - pd.to_datetime(last_restock_date[sp_key])).days
                restock_every             = restock_frequency_days(store_size)
                replenishment_multiplier  = 1.0
                applicable_discount_cap   = 30

                for pol in active_policies_today.itertuples(index=False):
                    if ((pol.affected_category  is None or pol.affected_category  == category) and
                        (pol.affected_store_type is None or pol.affected_store_type == store_type)):
                        replenishment_multiplier *= float(pol.replenishment_multiplier)
                        applicable_discount_cap   = min(applicable_discount_cap, int(pol.discount_cap_pct))

                ar = active_restrictions.get(sp_key)
                restriction_type = restriction_reason = restriction_severity = None
                restriction_active_flag = 0
                r_demand = r_replen = 1.0
                if ar:
                    restriction_type          = ar["restriction_type"]
                    restriction_reason        = ar["restriction_reason"]
                    restriction_severity      = ar["restriction_severity"]
                    restriction_active_flag   = 1
                    r_demand                  = ar["demand_multiplier"]
                    r_replen                  = ar["replenishment_multiplier"]

                restock_qty = 0
                if days_since_restock >= restock_every:
                    lo, hi        = target_inventory_days(category)
                    target_days   = np.random.randint(lo, hi+1)
                    desired_stock = max(1, int(round(base_demand_map[sp_key] * target_days * replenishment_multiplier * r_replen)))
                    if desired_stock > current_inventory:
                        restock_qty        = desired_stock - current_inventory
                        current_inventory += restock_qty
                    last_restock_date[sp_key] = current_date

                base = base_demand_map[sp_key]
                base *= 1.4 if store_size == "Large" else 1.1 if store_size == "Medium" else 0.9
                if category in ["Air Conditioners","Refrigerators"] and season == "Dry":          base *= 1.4
                if category in ["Televisions","Telecom Services"]   and month == 12:              base *= 1.5
                if category in ["Mobile Phones","Accessories"]      and month in [9, 12]:         base *= 1.2
                if is_weekend:                                                                     base *= 1.15
                if is_holiday:                                                                     base *= 1.3
                if category == "Air Conditioners" and temp > 30:                                   base *= 1.3
                if category == "Telecom Services" and rainfall > 5:                                base *= 1.1

                for pol in active_policies_today.itertuples(index=False):
                    if ((pol.affected_category  is None or pol.affected_category  == category) and
                        (pol.affected_store_type is None or pol.affected_store_type == store_type)):
                        base *= float(pol.demand_multiplier)

                base *= r_demand
                base *= weekly_store_multipliers[week_key]

                promo = promo_lookup.get((current_date, store_id, product_id))
                promo_flag = 0
                promo_type = None
                discount_pct = 0
                if promo:
                    promo_flag   = int(promo["promo_flag"])
                    promo_type   = promo["promo_type"]
                    discount_pct = min(int(promo["discount_pct"]), applicable_discount_cap)

                price = regular_price * (1 - discount_pct / 100.0)
                if discount_pct > 0:
                    base *= 1 + (discount_pct / 50.0)

                demand_mean     = max(0.01, base)
                potential_sales = max(0, int(round(max(0, np.random.normal(demand_mean, demand_mean * 0.3)))))

                if (np.random.rand() < base_stockout_probability(category) and
                        sp_key not in active_restrictions and np.random.rand() < 0.25):
                    new_type = weighted_choice(["Stock Restriction","Supply Delay","Promo Suspension","Category Cap"], [0.45,0.30,0.15,0.10])
                    new_sev  = weighted_choice(["Low","Medium","High"], [0.5,0.35,0.15])
                    if new_type == "Stock Restriction":  new_reason, dm, rm = "Low available inventory",  0.92, 0.70
                    elif new_type == "Supply Delay":     new_reason, dm, rm = "Replenishment delay",      0.97, 0.60
                    elif new_type == "Promo Suspension": new_reason, dm, rm = "Margin protection rule",   0.90, 1.00
                    else:                                new_reason, dm, rm = "Category-level control",   0.88, 0.85

                    dur = int(np.random.randint(2, 9))
                    active_restrictions[sp_key] = {
                        "restriction_type": new_type, "restriction_reason": new_reason,
                        "restriction_severity": new_sev, "start_date": current_date,
                        "end_date": current_date + pd.Timedelta(days=dur-1), "duration_days": dur,
                        "demand_multiplier": dm, "replenishment_multiplier": rm,
                    }
                    restriction_type = new_type; restriction_reason = new_reason
                    restriction_severity = new_sev; restriction_active_flag = 1
                    rows_restrictions.append({
                        "date": current_date, "store_id": store_id, "product_id": product_id,
                        "restriction_type": new_type, "restriction_reason": new_reason,
                        "restriction_severity": new_sev, "duration_days": dur, "active_flag": 1,
                    })

                if restriction_active_flag == 1 and restriction_type == "Promo Suspension":
                    promo_flag = 0; promo_type = None; discount_pct = 0; price = regular_price

                starting_inventory  = current_inventory
                units_sold          = min(starting_inventory, potential_sales)
                ending_inventory    = starting_inventory - units_sold
                stockout_flag       = int(units_sold < potential_sales)
                revenue             = round(units_sold * price, 2)
                inventory_state[sp_key] = ending_inventory

                rows_sales.append({
                    "date": current_date, "store_id": store_id, "product_id": product_id,
                    "units_sold": units_sold, "price": round(price, 2), "regular_price": regular_price,
                    "discount_pct": discount_pct, "promo_flag": promo_flag, "promo_type": promo_type,
                    "revenue": revenue, "starting_inventory": starting_inventory, "restock_qty": restock_qty,
                    "ending_inventory": ending_inventory, "stockout_occurred": stockout_flag,
                    "restriction_active": restriction_active_flag, "restriction_type": restriction_type,
                    "city": city, "store_size": store_size, "store_type": store_type, "category": category,
                })
                rows_inventory.append({
                    "date": current_date, "store_id": store_id, "product_id": product_id,
                    "starting_inventory": starting_inventory, "restock_qty": restock_qty,
                    "ending_inventory": ending_inventory, "stockout_flag": stockout_flag,
                })

    restriction_df = pd.DataFrame(rows_restrictions) if rows_restrictions else pd.DataFrame(
        columns=["date","store_id","product_id","restriction_type","restriction_reason",
                 "restriction_severity","duration_days","active_flag"])
    updated_state = {
        "inventory_state":          inventory_state,
        "base_demand_map":          base_demand_map,
        "last_restock_date":        {k: pd.to_datetime(v) for k, v in last_restock_date.items()},
        "active_restrictions":      active_restrictions,
        "weekly_store_multipliers": weekly_store_multipliers,
    }
    return pd.DataFrame(rows_sales), pd.DataFrame(rows_inventory), restriction_df, updated_state


# =========================================================
# 6. CUSTOMER ACTIVITY / STORE OPERATIONS
# =========================================================

def generate_customer_activity_forward(sales_df, calendar_df, stores_df, prior_active_customers=None):
    rows = []
    daily = sales_df.groupby(["date","store_id"], as_index=False).agg(
        total_units_sold=("units_sold","sum"), total_revenue=("revenue","sum"),
        promo_items=("promo_flag","sum"), stockout_items=("stockout_occurred","sum"),
        active_restrictions=("restriction_active","sum"),
    )
    daily["date"]     = pd.to_datetime(daily["date"])
    calendar_df       = calendar_df.copy()
    calendar_df["date"] = pd.to_datetime(calendar_df["date"])
    cal_lookup        = calendar_df.set_index("date").to_dict(orient="index")
    size_map          = stores_df.set_index("store_id")["store_size"].to_dict()
    prior_active      = {} if prior_active_customers is None else {int(k): int(v) for k, v in prior_active_customers.items()}

    for row in daily.sort_values(["date","store_id"]).itertuples(index=False):
        dm           = cal_lookup[row.date]
        store_size   = size_map.get(row.store_id, "Small")
        base_visits  = np.random.randint(120,250) if store_size=="Large" else np.random.randint(70,160) if store_size=="Medium" else np.random.randint(30,90)
        if dm["is_weekend"]: base_visits *= 1.15
        if dm["is_holiday"]: base_visits *= 1.20
        if dm["month"]==12:  base_visits *= 1.12
        promo_boost  = row.promo_items * np.random.uniform(0.8, 2.0)
        sales_signal = row.total_units_sold * np.random.uniform(0.2, 0.8)
        friction     = row.stockout_items * np.random.uniform(0.2, 0.8) + row.active_restrictions * np.random.uniform(0.1, 0.5)
        active       = max(5, int(base_visits + promo_boost + sales_signal - friction))
        prev         = prior_active.get(row.store_id, active)
        new_c        = max(0, int(active * np.random.uniform(0.10, 0.28)))
        prior_active[row.store_id] = active
        rows.append({
            "date": row.date, "store_id": row.store_id, "active_customers": active,
            "new_customers": new_c, "returning_customers": max(0, active - new_c),
            "churn_risk_customers": max(0, int(row.stockout_items * np.random.uniform(0.3, 1.3))),
            "net_customer_change": active - prev,
            "estimated_conversion_rate": round(row.total_units_sold / max(active, 1), 3),
            "daily_revenue": round(row.total_revenue, 2),
        })
    return pd.DataFrame(rows), prior_active


def generate_store_operations(customer_activity_df, stores_df, calendar_df, policy_regimes_df):
    rows = []
    customer_activity_df = customer_activity_df.copy()
    customer_activity_df["date"] = pd.to_datetime(customer_activity_df["date"])
    calendar_df = calendar_df.copy()
    calendar_df["date"] = pd.to_datetime(calendar_df["date"])
    if policy_regimes_df is None: policy_regimes_df = pd.DataFrame()
    policy_regimes_df = policy_regimes_df.copy()
    if not policy_regimes_df.empty:
        policy_regimes_df["start_date"] = pd.to_datetime(policy_regimes_df["start_date"], format="mixed")
        policy_regimes_df["end_date"]   = pd.to_datetime(policy_regimes_df["end_date"],   format="mixed")

    store_meta = stores_df.set_index("store_id").to_dict(orient="index")
    cal_lookup = calendar_df.set_index("date").to_dict(orient="index")

    for row in customer_activity_df.sort_values(["date","store_id"]).itertuples(index=False):
        store_size = store_meta[row.store_id]["store_size"]
        store_type = store_meta[row.store_id]["store_type"]
        staff = np.random.randint(12,25) if store_size=="Large" else np.random.randint(7,15) if store_size=="Medium" else np.random.randint(3,8)
        dm    = cal_lookup[row.date]
        if dm["is_weekend"]: staff = max(2, int(round(staff * np.random.uniform(0.90, 1.05))))
        if dm["is_holiday"]: staff = max(2, int(round(staff * np.random.uniform(0.85, 1.00))))
        sim   = 1.0
        active_pols = pd.DataFrame() if policy_regimes_df.empty else policy_regimes_df[
            (policy_regimes_df["start_date"] <= row.date) & (policy_regimes_df["end_date"] >= row.date)]
        for pol in active_pols.itertuples(index=False):
            if pol.affected_store_type is None or pol.affected_store_type == store_type:
                sim *= float(pol.service_intensity_multiplier)
        support  = max(0, int(row.active_customers * np.random.uniform(0.08, 0.20) * sim))
        missed   = max(0, int((support + row.churn_risk_customers) * np.random.uniform(0.03, 0.15)))
        rows.append({
            "date": row.date, "store_id": row.store_id, "staff_on_duty": staff,
            "customer_visits": row.active_customers, "support_requests": support,
            "completed_interactions": max(0, support - missed), "missed_interactions": missed,
            "service_pressure_score": round((row.active_customers + support) / max(staff, 1), 2),
        })
    return pd.DataFrame(rows)


# =========================================================
# 7. MAIN PIPELINE
# =========================================================

def main():
    ensure_dataset()

    if RESET_DB:
        reset_bigquery_tables()

    prior_state = load_generator_state()
    initialize_rng(prior_state)

    last_generated_date, forward_start, forward_end = get_effective_forward_window(
        USER_START_DATE, USER_END_DATE, prior_state
    )

    if forward_start is None:
        print("No new dates to generate — BigQuery is already up to date.")
        if last_generated_date:
            print(f"Last generated date: {pd.to_datetime(last_generated_date).date()}")
        return

    print(f"Forward generation window: {forward_start.date()} → {forward_end.date()}")

    stores_df   = load_or_create_dim("dim_stores",   lambda: generate_stores(N_STORES_EXTRA))
    products_df = load_or_create_dim("dim_products", lambda: generate_products(N_PRODUCTS))
    store_products_df = load_or_create_dim("dim_store_products",
                            lambda: generate_store_product_assortment(stores_df, products_df))

    calendar_df      = generate_calendar(str(forward_start.date()), str(forward_end.date()))
    weather_df       = generate_weather(calendar_df, stores_df)
    promotions_df    = generate_promotions(calendar_df, stores_df, products_df)
    policy_regimes_df = load_policy_regimes(calendar_df)

    sales_df, inventory_df, restriction_df, updated_state = sales_inventory_and_restrictions_forward(
        calendar_df, stores_df, products_df, weather_df, promotions_df, policy_regimes_df,
        store_products_df, prior_state
    )

    customer_activity_df, updated_prior_active = generate_customer_activity_forward(
        sales_df, calendar_df, stores_df,
        prior_active_customers=(prior_state or {}).get("prior_active_customers"),
    )

    store_operations_df = generate_store_operations(
        customer_activity_df, stores_df, calendar_df, policy_regimes_df
    )

    upload_to_bigquery(calendar_df,           "dim_calendar")
    upload_to_bigquery(weather_df,            "fact_weather")
    upload_to_bigquery(promotions_df,         "fact_promotions")
    upload_to_bigquery(sales_df,              "fact_sales")
    upload_to_bigquery(inventory_df,          "fact_inventory")
    upload_to_bigquery(customer_activity_df,  "fact_customer_activity")
    upload_to_bigquery(store_operations_df,   "fact_store_operations")
    upload_to_bigquery(restriction_df,        "fact_restriction_events")

    save_generator_state({
        "inventory_state":          updated_state["inventory_state"],
        "base_demand_map":          updated_state["base_demand_map"],
        "last_restock_date":        updated_state["last_restock_date"],
        "active_restrictions":      updated_state["active_restrictions"],
        "weekly_store_multipliers": updated_state["weekly_store_multipliers"],
        "prior_active_customers":   updated_prior_active,
        "last_generated_date":      pd.to_datetime(calendar_df["date"]).max(),
        "rng_state":                np.random.get_state(),
    })

    print(f"\nBigQuery generation complete: {forward_start.date()} → {forward_end.date()}")
    print(f"  calendar={len(calendar_df):,}  weather={len(weather_df):,}  promotions={len(promotions_df):,}")
    print(f"  sales={len(sales_df):,}  inventory={len(inventory_df):,}  customer_activity={len(customer_activity_df):,}")
    print(f"  store_operations={len(store_operations_df):,}  restriction_events={len(restriction_df):,}")


if __name__ == "__main__":
    main()
