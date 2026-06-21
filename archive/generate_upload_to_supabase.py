# generate_upload_to_supabase.py

import sys
import os
import pickle
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus
from uuid import uuid4

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text


# =========================================================
# CONFIG
# =========================================================

SEED = 42

SCALE_MODE = os.getenv("SCALE_MODE", "small").lower()
RESET_DB = os.getenv("RESET_DB", "false").lower() == "true"

print(f"🔧 Running SunnyBest direct Supabase generator in SCALE_MODE={SCALE_MODE}")

DEFAULT_START_DATE = "2021-01-01"
DEFAULT_END_DATE = datetime.today().strftime("%Y-%m-%d")

if len(sys.argv) >= 3:
    USER_START_DATE = sys.argv[1]
    USER_END_DATE = sys.argv[2]
    print(f"📅 Using custom requested date range: {USER_START_DATE} → {USER_END_DATE}")
else:
    USER_START_DATE = DEFAULT_START_DATE
    USER_END_DATE = DEFAULT_END_DATE
    print(f"📅 Using default requested date range: {USER_START_DATE} → {USER_END_DATE}")

N_PRODUCTS = 120
N_STORES_EXTRA = 0

STATE_DIR = "data/state/"
STATE_FILE = "sunnybest_generator_state.pkl"

if SCALE_MODE == "large":
    if len(sys.argv) < 3:
        USER_START_DATE = "2018-01-01"
        USER_END_DATE = datetime.today().strftime("%Y-%m-%d")
    N_PRODUCTS = 800
    N_STORES_EXTRA = 43


# =========================================================
# SUPABASE CONNECTION
# =========================================================

host = "aws-1-eu-central-1.pooler.supabase.com"
port = 5432
database = "postgres"
user = "postgres.ogkdfmkybqtrsglcizzt"

password = quote_plus(os.getenv("SUPABASE_DB_PASSWORD", ""))

if not password:
    raise ValueError("SUPABASE_DB_PASSWORD is not set.")

SUPABASE_DB_URL = (
    f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
)

engine = create_engine(SUPABASE_DB_URL, pool_pre_ping=True)


# =========================================================
# STATE HELPERS
# =========================================================

def get_state_path(state_dir: str = STATE_DIR, state_file: str = STATE_FILE) -> Path:
    path = Path(state_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path / state_file


def load_generator_state(state_dir: str = STATE_DIR, state_file: str = STATE_FILE):
    state_path = get_state_path(state_dir, state_file)
    if not state_path.exists():
        return None
    with open(state_path, "rb") as f:
        state = pickle.load(f)
    print(f"📦 Loaded generator state from: {state_path}")
    return state


def save_generator_state(state: dict, state_dir: str = STATE_DIR, state_file: str = STATE_FILE) -> Path:
    state_path = get_state_path(state_dir, state_file)
    with open(state_path, "wb") as f:
        pickle.dump(state, f)
    print(f"💾 Saved generator state to: {state_path}")
    return state_path


def delete_generator_state():
    state_path = get_state_path()
    if state_path.exists():
        state_path.unlink()
        print(f"🧹 Deleted generator state: {state_path}")


def initialize_rng(prior_state: dict | None):
    if prior_state and "rng_state" in prior_state:
        np.random.set_state(prior_state["rng_state"])
        print("🎲 Restored numpy RNG state from prior run.")
    else:
        np.random.seed(SEED)
        print(f"🎲 Initialized numpy RNG with seed={SEED}.")


def get_effective_forward_window(user_start_date: str, user_end_date: str, prior_state: dict | None):
    requested_start = pd.to_datetime(user_start_date)
    requested_end = pd.to_datetime(user_end_date)

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
# SUPABASE HELPERS
# =========================================================

def ensure_core_schema():
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS core;"))


def reset_supabase_tables():
    print("🧨 RESET_DB=true detected. Clearing SunnyBest Supabase tables...")

    tables = [
        "fact_sales",
        "fact_inventory",
        "fact_customer_activity",
        "fact_store_operations",
        "fact_promotions",
        "fact_weather",
        "fact_restriction_events",
        "dim_calendar",
        "dim_policy_regimes",
        "dim_products",
        "dim_stores",
    ]

    with engine.begin() as conn:
        for table in tables:
            conn.execute(text(f"DROP TABLE IF EXISTS core.{table} CASCADE;"))

    state_path = get_state_path()
    if state_path.exists():
        state_path.unlink()
        print(f"🗑️ Deleted local generator state: {state_path}")

    print("✅ Reset complete.")


def table_has_rows(table_name: str) -> bool:
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT EXISTS (SELECT 1 FROM core.{table_name} LIMIT 1)"))
            return bool(result.scalar())
    except Exception:
        return False


def load_table(table_name: str) -> pd.DataFrame:
    return pd.read_sql(f"SELECT * FROM core.{table_name}", engine)


UNIQUE_KEYS = {
    "dim_calendar": ["date"],
    "dim_stores": ["store_id"],
    "dim_products": ["product_id"],
    "dim_policy_regimes": ["policy_id"],
    "fact_weather": ["date", "city"],
    "fact_promotions": ["date", "store_id", "product_id"],
    "fact_sales": ["date", "store_id", "product_id"],
    "fact_inventory": ["date", "store_id", "product_id"],
    "fact_customer_activity": ["date", "store_id"],
    "fact_store_operations": ["date", "store_id"],
    "fact_restriction_events": ["date", "store_id", "product_id", "restriction_type"],
}


def ensure_table_exists(df: pd.DataFrame, table_name: str):
    """Create an empty table from the dataframe structure if the table does not exist."""
    if df is None or df.empty:
        return

    with engine.begin() as conn:
        df.head(0).to_sql(
            name=table_name,
            con=conn,
            schema="core",
            if_exists="append",
            index=False,
        )


def ensure_unique_index(table_name: str):
    """Create a unique index so reruns do not duplicate rows."""
    keys = UNIQUE_KEYS.get(table_name)
    if not keys:
        return

    index_name = f"ux_{table_name}_{'_'.join(keys)}"
    columns = ", ".join(keys)

    with engine.begin() as conn:
        conn.execute(text(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} ON core.{table_name} ({columns});"
        ))


def upload_to_supabase(df: pd.DataFrame, table_name: str, batch_size: int = 5000):
    """
    Safe append upload:
    - uploads in smaller batches
    - uses a fresh transaction per batch
    - uses a temporary staging table per batch
    - inserts with ON CONFLICT DO NOTHING to avoid duplicates
    - does NOT delete existing rows
    """
    if df is None or df.empty:
        print(f"⚠️ No rows for core.{table_name} — skipping.")
        return

    df = df.copy()

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])

    ensure_table_exists(df, table_name)
    ensure_unique_index(table_name)

    total_rows = len(df)
    columns = list(df.columns)
    column_sql = ", ".join([f'"{c}"' for c in columns])

    print(f"⬆️ Uploading {total_rows:,} rows -> core.{table_name} in safe batches of {batch_size:,}")

    for start in range(0, total_rows, batch_size):
        end = min(start + batch_size, total_rows)
        batch = df.iloc[start:end].copy()
        temp_table = f"tmp_{table_name}_{uuid4().hex[:10]}"

        with engine.begin() as conn:
            batch.to_sql(
                name=temp_table,
                con=conn,
                schema="core",
                if_exists="replace",
                index=False,
                chunksize=1000,
            )

            conn.execute(text(f"""
                INSERT INTO core.{table_name} ({column_sql})
                SELECT {column_sql}
                FROM core.{temp_table}
                ON CONFLICT DO NOTHING;
            """))

            conn.execute(text(f"DROP TABLE IF EXISTS core.{temp_table};"))

        print(f"✅ Uploaded rows {start + 1:,} to {end:,} of {total_rows:,} -> core.{table_name}")

    print(f"✅ Done: core.{table_name}")


def load_or_create_dim_from_supabase(table_name: str, generator_func):
    if table_has_rows(table_name):
        df = load_table(table_name)
        print(f"📥 Loaded core.{table_name} from Supabase ({len(df):,} rows)")
        return df

    print(f"🆕 core.{table_name} is empty or missing — generating once.")
    df = generator_func()
    upload_to_supabase(df, table_name)
    return df


def load_policy_regimes_from_supabase(calendar_df: pd.DataFrame):
    if not table_has_rows("dim_policy_regimes"):
        print("🆕 No policy regimes found. Generating initial policies once.")
        initial_policies = generate_policy_regimes(calendar_df)
        upload_to_supabase(initial_policies, "dim_policy_regimes")
        return initial_policies

    existing = load_table("dim_policy_regimes")
    existing = existing.copy()
    existing["start_date"] = pd.to_datetime(existing["start_date"], format="mixed")
    existing["end_date"] = pd.to_datetime(existing["end_date"], format="mixed")

    window_start = pd.to_datetime(calendar_df["date"].min())
    window_end = pd.to_datetime(calendar_df["date"].max())

    active_policies = existing[
        (existing["start_date"] <= window_end) &
        (existing["end_date"] >= window_start)
    ].copy()

    print(f"📜 Loaded {len(active_policies):,} active policy regimes for this window.")
    return active_policies


# =========================================================
# 1. STORES
# =========================================================

def generate_stores(n_extra: int = 0) -> pd.DataFrame:
    stores_list = [
        {"store_id": 1, "store_name": "SunnyBest Benin Main", "city": "Benin", "area": "Oredo", "region": "Edo South", "store_type": "Mall", "store_size": "Large"},
        {"store_id": 2, "store_name": "SunnyBest Ekpoma", "city": "Ekpoma", "area": "Esan West", "region": "Edo Central", "store_type": "High Street", "store_size": "Medium"},
        {"store_id": 3, "store_name": "SunnyBest Auchi", "city": "Auchi", "area": "Etsako West", "region": "Edo North", "store_type": "High Street", "store_size": "Medium"},
        {"store_id": 4, "store_name": "SunnyBest Irrua", "city": "Irrua", "area": "Esan Central", "region": "Edo Central", "store_type": "Plaza", "store_size": "Small"},
        {"store_id": 5, "store_name": "SunnyBest Igueben", "city": "Igueben", "area": "Igueben", "region": "Edo Central", "store_type": "High Street", "store_size": "Small"},
        {"store_id": 6, "store_name": "SunnyBest Agenebode", "city": "Agenebode", "area": "Etsako East", "region": "Edo North", "store_type": "Plaza", "store_size": "Small"},
        {"store_id": 7, "store_name": "SunnyBest Ogwa", "city": "Ogwa", "area": "Esan West", "region": "Edo Central", "store_type": "High Street", "store_size": "Small"},
    ]
    base = pd.DataFrame(stores_list)

    if n_extra <= 0:
        return base

    cities = base["city"].unique().tolist()
    store_types = base["store_type"].unique().tolist()
    store_sizes = base["store_size"].unique().tolist()
    regions = base["region"].unique().tolist()
    areas = base["area"].unique().tolist()
    start_id = int(base["store_id"].max()) + 1

    extra_rows = []
    for i in range(n_extra):
        sid = start_id + i
        city = np.random.choice(cities)
        extra_rows.append({
            "store_id": sid,
            "store_name": f"SunnyBest {city} Branch {sid}",
            "city": city,
            "area": np.random.choice(areas),
            "region": np.random.choice(regions),
            "store_type": np.random.choice(store_types),
            "store_size": np.random.choice(store_sizes),
        })

    return pd.concat([base, pd.DataFrame(extra_rows)], ignore_index=True)


# =========================================================
# 2. PRODUCTS
# =========================================================

CATEGORIES = {
    "Mobile Phones": ["Samsung", "Apple", "Tecno", "Infinix", "Itel"],
    "Laptops & Computers": ["HP", "Dell", "Lenovo", "Acer", "Asus"],
    "Televisions": ["LG", "Samsung", "Hisense", "Sony"],
    "Refrigerators": ["LG", "Hisense", "Haier Thermocool"],
    "Air Conditioners": ["LG", "Hisense", "Panasonic"],
    "Small Appliances": ["Binatone", "Philips", "Century"],
    "Network Devices": ["Huawei", "ZTE", "TP-Link"],
    "Accessories": ["Oraimo", "Anker", "Generic"],
    "Telecom Services": ["MTN", "Glo", "Airtel", "9mobile"],
}

CATEGORY_WEIGHTS = {
    "Mobile Phones": 0.20,
    "Laptops & Computers": 0.15,
    "Televisions": 0.10,
    "Refrigerators": 0.08,
    "Air Conditioners": 0.07,
    "Small Appliances": 0.15,
    "Network Devices": 0.10,
    "Accessories": 0.10,
    "Telecom Services": 0.05,
}


def generate_products(n_products: int) -> pd.DataFrame:
    rows = []
    product_id = 1001
    cat_list = list(CATEGORY_WEIGHTS.keys())
    weights = list(CATEGORY_WEIGHTS.values())

    for _ in range(n_products):
        cat = np.random.choice(cat_list, p=weights)
        brand = np.random.choice(CATEGORIES[cat])

        if cat == "Mobile Phones":
            regular_price = np.random.randint(40000, 250000)
        elif cat == "Laptops & Computers":
            regular_price = np.random.randint(120000, 450000)
        elif cat == "Televisions":
            regular_price = np.random.randint(60000, 300000)
        elif cat in ["Refrigerators", "Air Conditioners"]:
            regular_price = np.random.randint(90000, 350000)
        elif cat == "Small Appliances":
            regular_price = np.random.randint(8000, 45000)
        elif cat == "Network Devices":
            regular_price = np.random.randint(10000, 70000)
        elif cat == "Accessories":
            regular_price = np.random.randint(2000, 20000)
        elif cat == "Telecom Services":
            regular_price = np.random.randint(500, 10000)
        else:
            regular_price = np.random.randint(10000, 200000)

        cost_price = int(regular_price * np.random.uniform(0.6, 0.8))
        is_seasonal = int(cat in ["Air Conditioners", "Refrigerators", "Televisions", "Mobile Phones", "Telecom Services"])
        warranty_months = np.random.choice([6, 12, 24])
        product_name = f"{brand} {cat.split()[0]} Model-{np.random.randint(100, 999)}"

        rows.append({
            "product_id": product_id,
            "product_name": product_name,
            "category": cat,
            "brand": brand,
            "regular_price": regular_price,
            "cost_price": cost_price,
            "is_seasonal": is_seasonal,
            "warranty_months": warranty_months,
        })
        product_id += 1

    return pd.DataFrame(rows)


# =========================================================
# 3. CALENDAR / WEATHER / PROMOTIONS / POLICIES
# =========================================================

def generate_calendar(start_date: str, end_date: str) -> pd.DataFrame:
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    cal = pd.DataFrame({"date": dates})
    cal["year"] = cal["date"].dt.year
    cal["month"] = cal["date"].dt.month
    cal["day"] = cal["date"].dt.day
    cal["day_of_week"] = cal["date"].dt.day_name()
    cal["day_of_week_num"] = cal["date"].dt.weekday
    cal["week_of_year"] = cal["date"].dt.isocalendar().week.astype(int)
    cal["is_weekend"] = cal["day_of_week"].isin(["Saturday", "Sunday"])

    fixed_holidays = {"01-01", "05-01", "10-01", "12-25", "12-26"}
    cal["is_holiday"] = cal["date"].apply(lambda d: d.strftime("%m-%d") in fixed_holidays)
    cal["is_payday"] = cal["day"] == 25

    def season(m):
        if m in [11, 12, 1, 2]:
            return "Dry"
        if m in [3, 4, 5, 6, 7]:
            return "Early Rainy"
        return "Late Rainy"

    cal["season"] = cal["month"].apply(season)
    cal["is_black_friday_period"] = (cal["month"] == 11) & (cal["day_of_week"] == "Friday")
    return cal


def generate_weather(calendar_df: pd.DataFrame, stores_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, store in stores_df.iterrows():
        city = store["city"]
        for _, day in calendar_df.iterrows():
            month = day["month"]
            base_temp = 30 if month in [1, 2, 3] else 29 if month in [4, 5, 6] else 27 if month in [7, 8, 9] else 28
            temperature = base_temp + np.random.normal(0, 1.5)
            rainfall = max(0, np.random.normal(5, 5)) if month in [4, 5, 6, 7, 8, 9] else max(0, np.random.normal(1, 2))
            condition = "Sunny" if rainfall == 0 else "Cloudy" if rainfall < 3 else "Rainy"
            rows.append({
                "date": day["date"],
                "city": city,
                "temperature_c": round(temperature, 1),
                "rainfall_mm": round(rainfall, 1),
                "weather_condition": condition,
            })
    return pd.DataFrame(rows)


def generate_promotions(calendar_df: pd.DataFrame, stores_df: pd.DataFrame, products_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, day in calendar_df.iterrows():
        promo_probability = 0.01
        if day["is_weekend"]:
            promo_probability += 0.02
        if day["is_holiday"]:
            promo_probability += 0.05
        if day["is_black_friday_period"]:
            promo_probability += 0.10
        if day["month"] == 12:
            promo_probability += 0.04

        if np.random.rand() < promo_probability:
            n_promos = np.random.randint(3, 15)
            store_ids = np.random.choice(stores_df["store_id"], size=n_promos, replace=True)
            product_ids = np.random.choice(products_df["product_id"], size=n_promos, replace=True)
            for sid, pid in zip(store_ids, product_ids):
                promo_type = np.random.choice(["Discount", "Bundle", "Free Accessory", "Price Slash"], p=[0.6, 0.15, 0.15, 0.10])
                discount_pct = np.random.choice([5, 10, 15, 20, 25, 30]) if promo_type in ["Discount", "Price Slash"] else 0
                rows.append({
                    "date": day["date"],
                    "store_id": int(sid),
                    "product_id": int(pid),
                    "promo_type": promo_type,
                    "discount_pct": discount_pct,
                    "promo_flag": 1,
                })

    if not rows:
        return pd.DataFrame(columns=["date", "store_id", "product_id", "promo_type", "discount_pct", "promo_flag"])
    return pd.DataFrame(rows).drop_duplicates(subset=["date", "store_id", "product_id"]).reset_index(drop=True)


def generate_policy_regimes(calendar_df: pd.DataFrame) -> pd.DataFrame:
    min_date = calendar_df["date"].min()
    max_date = calendar_df["date"].max()
    candidate_policies = [
        {"policy_name": "Telecom Seasonal Push", "affected_category": "Telecom Services", "affected_store_type": None, "demand_multiplier": 1.15, "discount_cap_pct": 20, "replenishment_multiplier": 1.10, "service_intensity_multiplier": 1.08},
        {"policy_name": "Premium Electronics Margin Protection", "affected_category": "Mobile Phones", "affected_store_type": None, "demand_multiplier": 0.96, "discount_cap_pct": 10, "replenishment_multiplier": 0.95, "service_intensity_multiplier": 1.02},
        {"policy_name": "Mall Expansion Drive", "affected_category": None, "affected_store_type": "Mall", "demand_multiplier": 1.08, "discount_cap_pct": 25, "replenishment_multiplier": 1.12, "service_intensity_multiplier": 1.10},
        {"policy_name": "Small Store Inventory Control", "affected_category": None, "affected_store_type": "Plaza", "demand_multiplier": 0.98, "discount_cap_pct": 15, "replenishment_multiplier": 0.88, "service_intensity_multiplier": 1.00},
        {"policy_name": "Cooling Appliances Availability Programme", "affected_category": "Air Conditioners", "affected_store_type": None, "demand_multiplier": 1.10, "discount_cap_pct": 20, "replenishment_multiplier": 1.20, "service_intensity_multiplier": 1.05},
    ]
    selected = np.random.choice(len(candidate_policies), size=min(4, len(candidate_policies)), replace=False)
    windows = []
    total_days = max(1, (max_date - min_date).days)
    for i, idx in enumerate(selected, start=1):
        policy = candidate_policies[idx]
        start_offset = np.random.randint(0, max(1, total_days))
        duration = np.random.randint(90, 240)
        start_date = min_date + pd.Timedelta(days=int(start_offset))
        end_date = min(start_date + pd.Timedelta(days=int(duration)), max_date)
        windows.append({"policy_id": i, "start_date": start_date, "end_date": end_date, **policy})
    return pd.DataFrame(windows)


# =========================================================
# 4. DEMAND / INVENTORY HELPERS
# =========================================================

def base_demand_for_category(category: str) -> float:
    if category == "Mobile Phones": return np.random.uniform(0.5, 3.0)
    if category == "Laptops & Computers": return np.random.uniform(0.2, 1.0)
    if category == "Televisions": return np.random.uniform(0.1, 0.8)
    if category in ["Refrigerators", "Air Conditioners"]: return np.random.uniform(0.05, 0.5)
    if category == "Small Appliances": return np.random.uniform(0.5, 4.0)
    if category == "Network Devices": return np.random.uniform(0.2, 2.0)
    if category == "Accessories": return np.random.uniform(1.0, 8.0)
    if category == "Telecom Services": return np.random.uniform(5.0, 30.0)
    return np.random.uniform(0.5, 3.0)


def target_inventory_days(category: str):
    if category in ["Mobile Phones", "Network Devices", "Accessories", "Telecom Services"]: return 4, 10
    if category in ["Laptops & Computers", "Televisions"]: return 6, 14
    if category in ["Refrigerators", "Air Conditioners"]: return 7, 16
    return 5, 12


def base_stockout_probability(category: str) -> float:
    if category in ["Mobile Phones", "Network Devices", "Accessories", "Telecom Services"]: return 0.08
    if category in ["Laptops & Computers", "Televisions"]: return 0.05
    return 0.03


def restock_frequency_days(store_size: str) -> int:
    if store_size == "Large": return 3
    if store_size == "Medium": return 5
    return 7


# =========================================================
# 5. SALES / INVENTORY / RESTRICTIONS
# =========================================================

def sales_inventory_and_restrictions_forward(calendar_df, stores_df, products_df, weather_df, promotions_df, policy_regimes_for_logic_df, prior_state=None):
    rows_sales, rows_inventory, rows_restrictions = [], [], []

    weather_lookup = {(pd.to_datetime(row.date), row.city): (row.temperature_c, row.rainfall_mm, row.weather_condition) for row in weather_df.itertuples(index=False)}
    promo_lookup = {(pd.to_datetime(row.date), row.store_id, row.product_id): {"promo_type": row.promo_type, "discount_pct": row.discount_pct, "promo_flag": row.promo_flag} for row in promotions_df.itertuples(index=False)}

    if prior_state is None:
        inventory_state, base_demand_map, last_restock_date, active_restrictions = {}, {}, {}, {}
        print("🆕 No prior state found. Initializing generator from scratch.")
    else:
        inventory_state = {parse_key(k): v for k, v in prior_state.get("inventory_state", {}).items()}
        base_demand_map = {parse_key(k): v for k, v in prior_state.get("base_demand_map", {}).items()}
        last_restock_date = {parse_key(k): pd.to_datetime(v) for k, v in prior_state.get("last_restock_date", {}).items()}
        active_restrictions = {parse_key(k): v for k, v in prior_state.get("active_restrictions", {}).items()}
        for _, v in active_restrictions.items():
            v["start_date"] = pd.to_datetime(v["start_date"])
            v["end_date"] = pd.to_datetime(v["end_date"])
        print("♻️ Continuing generation from prior saved state.")

    for store in stores_df.itertuples(index=False):
        for product in products_df.itertuples(index=False):
            key = (store.store_id, product.product_id)
            if key not in base_demand_map:
                base_demand_map[key] = base_demand_for_category(product.category)
            if key not in inventory_state:
                low_days, high_days = target_inventory_days(product.category)
                inventory_state[key] = max(1, int(round(base_demand_map[key] * np.random.randint(low_days, high_days + 1))))
            if key not in last_restock_date:
                last_restock_date[key] = pd.to_datetime(calendar_df["date"].min()) - pd.Timedelta(days=np.random.randint(1, 7))

    all_dates = sorted(pd.to_datetime(calendar_df["date"]).tolist())

    for current_date in all_dates:
        day = calendar_df.loc[pd.to_datetime(calendar_df["date"]) == current_date].iloc[0]
        month, is_weekend, is_holiday, season = int(day["month"]), bool(day["is_weekend"]), bool(day["is_holiday"]), day["season"]

        expired_keys = [k for k, v in active_restrictions.items() if current_date > pd.to_datetime(v["end_date"])]
        for e_key in expired_keys:
            del active_restrictions[e_key]

        if policy_regimes_for_logic_df is None or policy_regimes_for_logic_df.empty:
            active_policies_today = pd.DataFrame()
        else:
            active_policies_today = policy_regimes_for_logic_df[
                (pd.to_datetime(policy_regimes_for_logic_df["start_date"]) <= current_date) &
                (pd.to_datetime(policy_regimes_for_logic_df["end_date"]) >= current_date)
            ]

        for store in stores_df.itertuples(index=False):
            store_id, city, store_size, store_type = store.store_id, store.city, store.store_size, store.store_type
            temp, rainfall, _condition = weather_lookup.get((current_date, city), (28.0, 2.0, "Cloudy"))

            for product in products_df.itertuples(index=False):
                product_id, category, regular_price = product.product_id, product.category, product.regular_price
                sp_key = (store_id, product_id)
                current_inventory = inventory_state[sp_key]

                days_since_restock = (current_date - pd.to_datetime(last_restock_date[sp_key])).days
                restock_every = restock_frequency_days(store_size)
                replenishment_multiplier, applicable_discount_cap = 1.0, 30

                for policy in active_policies_today.itertuples(index=False):
                    category_match = (policy.affected_category is None) or (policy.affected_category == category)
                    store_type_match = (policy.affected_store_type is None) or (policy.affected_store_type == store_type)
                    if category_match and store_type_match:
                        replenishment_multiplier *= float(policy.replenishment_multiplier)
                        applicable_discount_cap = min(applicable_discount_cap, int(policy.discount_cap_pct))

                active_restriction = active_restrictions.get(sp_key)
                restriction_type, restriction_reason, restriction_severity = None, None, None
                restriction_active_flag = 0
                restriction_multiplier_demand, restriction_multiplier_replenishment = 1.0, 1.0

                if active_restriction:
                    restriction_type = active_restriction["restriction_type"]
                    restriction_reason = active_restriction["restriction_reason"]
                    restriction_severity = active_restriction["restriction_severity"]
                    restriction_active_flag = 1
                    restriction_multiplier_demand = active_restriction["demand_multiplier"]
                    restriction_multiplier_replenishment = active_restriction["replenishment_multiplier"]

                restock_qty = 0
                if days_since_restock >= restock_every:
                    low_days, high_days = target_inventory_days(category)
                    target_days = np.random.randint(low_days, high_days + 1)
                    desired_stock = max(1, int(round(base_demand_map[sp_key] * target_days * replenishment_multiplier * restriction_multiplier_replenishment)))
                    if desired_stock > current_inventory:
                        restock_qty = desired_stock - current_inventory
                        current_inventory += restock_qty
                    last_restock_date[sp_key] = current_date

                base = base_demand_map[sp_key]
                base *= 1.4 if store_size == "Large" else 1.1 if store_size == "Medium" else 0.9
                if category in ["Air Conditioners", "Refrigerators"] and season == "Dry": base *= 1.4
                if category in ["Televisions", "Telecom Services"] and month == 12: base *= 1.5
                if category in ["Mobile Phones", "Accessories"] and month in [9, 12]: base *= 1.2
                if is_weekend: base *= 1.15
                if is_holiday: base *= 1.3
                if category == "Air Conditioners" and temp > 30: base *= 1.3
                if category == "Telecom Services" and rainfall > 5: base *= 1.1

                for policy in active_policies_today.itertuples(index=False):
                    category_match = (policy.affected_category is None) or (policy.affected_category == category)
                    store_type_match = (policy.affected_store_type is None) or (policy.affected_store_type == store_type)
                    if category_match and store_type_match:
                        base *= float(policy.demand_multiplier)

                base *= restriction_multiplier_demand

                promo = promo_lookup.get((current_date, store_id, product_id))
                promo_flag, promo_type, discount_pct = 0, None, 0
                if promo:
                    promo_flag = int(promo["promo_flag"])
                    promo_type = promo["promo_type"]
                    discount_pct = min(int(promo["discount_pct"]), applicable_discount_cap)

                price = regular_price * (1 - discount_pct / 100.0)
                if discount_pct > 0:
                    base *= 1 + (discount_pct / 50.0)

                demand_mean = max(0.01, base)
                potential_sales = max(0, int(round(max(0, np.random.normal(demand_mean, demand_mean * 0.3)))))

                if np.random.rand() < base_stockout_probability(category) and sp_key not in active_restrictions and np.random.rand() < 0.25:
                    new_type = weighted_choice(["Stock Restriction", "Supply Delay", "Promo Suspension", "Category Cap"], [0.45, 0.30, 0.15, 0.10])
                    new_severity = weighted_choice(["Low", "Medium", "High"], [0.5, 0.35, 0.15])
                    if new_type == "Stock Restriction":
                        new_reason, demand_mult, replen_mult = "Low available inventory", 0.92, 0.70
                    elif new_type == "Supply Delay":
                        new_reason, demand_mult, replen_mult = "Replenishment delay", 0.97, 0.60
                    elif new_type == "Promo Suspension":
                        new_reason, demand_mult, replen_mult = "Margin protection rule", 0.90, 1.00
                    else:
                        new_reason, demand_mult, replen_mult = "Category-level control", 0.88, 0.85

                    duration_days = int(np.random.randint(2, 9))
                    active_restrictions[sp_key] = {
                        "restriction_type": new_type,
                        "restriction_reason": new_reason,
                        "restriction_severity": new_severity,
                        "start_date": current_date,
                        "end_date": current_date + pd.Timedelta(days=duration_days - 1),
                        "duration_days": duration_days,
                        "demand_multiplier": demand_mult,
                        "replenishment_multiplier": replen_mult,
                    }
                    restriction_type, restriction_reason, restriction_severity, restriction_active_flag = new_type, new_reason, new_severity, 1
                    rows_restrictions.append({
                        "date": current_date,
                        "store_id": store_id,
                        "product_id": product_id,
                        "restriction_type": new_type,
                        "restriction_reason": new_reason,
                        "restriction_severity": new_severity,
                        "duration_days": duration_days,
                        "active_flag": 1,
                    })

                if restriction_active_flag == 1 and restriction_type == "Promo Suspension":
                    promo_flag, promo_type, discount_pct, price = 0, None, 0, regular_price

                starting_inventory = current_inventory
                units_sold = min(starting_inventory, potential_sales)
                ending_inventory = starting_inventory - units_sold
                stockout_flag = int(units_sold < potential_sales)
                revenue = round(units_sold * price, 2)
                inventory_state[sp_key] = ending_inventory

                rows_sales.append({
                    "date": current_date,
                    "store_id": store_id,
                    "product_id": product_id,
                    "units_sold": units_sold,
                    "price": round(price, 2),
                    "regular_price": regular_price,
                    "discount_pct": discount_pct,
                    "promo_flag": promo_flag,
                    "promo_type": promo_type,
                    "revenue": revenue,
                    "starting_inventory": starting_inventory,
                    "restock_qty": restock_qty,
                    "ending_inventory": ending_inventory,
                    "stockout_occurred": stockout_flag,
                    "restriction_active": restriction_active_flag,
                    "restriction_type": restriction_type,
                    "city": city,
                    "store_size": store_size,
                    "store_type": store_type,
                    "category": category,
                })

                rows_inventory.append({
                    "date": current_date,
                    "store_id": store_id,
                    "product_id": product_id,
                    "starting_inventory": starting_inventory,
                    "restock_qty": restock_qty,
                    "ending_inventory": ending_inventory,
                    "stockout_flag": stockout_flag,
                })

    restriction_events_df = pd.DataFrame(rows_restrictions) if rows_restrictions else pd.DataFrame(columns=["date", "store_id", "product_id", "restriction_type", "restriction_reason", "restriction_severity", "duration_days", "active_flag"])
    updated_state = {
        "inventory_state": inventory_state,
        "base_demand_map": base_demand_map,
        "last_restock_date": {k: pd.to_datetime(v) for k, v in last_restock_date.items()},
        "active_restrictions": active_restrictions,
    }
    return pd.DataFrame(rows_sales), pd.DataFrame(rows_inventory), restriction_events_df, updated_state


# =========================================================
# 6. CUSTOMER ACTIVITY / STORE OPERATIONS
# =========================================================

def generate_customer_activity_forward(sales_df, calendar_df, stores_df, prior_active_customers=None):
    rows = []
    daily_store_sales = sales_df.groupby(["date", "store_id"], as_index=False).agg(
        total_units_sold=("units_sold", "sum"),
        total_revenue=("revenue", "sum"),
        promo_items=("promo_flag", "sum"),
        stockout_items=("stockout_occurred", "sum"),
        active_restrictions=("restriction_active", "sum"),
    )
    daily_store_sales["date"] = pd.to_datetime(daily_store_sales["date"])
    calendar_df = calendar_df.copy()
    calendar_df["date"] = pd.to_datetime(calendar_df["date"])
    calendar_lookup = calendar_df.set_index("date").to_dict(orient="index")
    store_size_map = stores_df.set_index("store_id")["store_size"].to_dict()
    prior_active = {} if prior_active_customers is None else {int(k): int(v) for k, v in prior_active_customers.items()}

    for row in daily_store_sales.sort_values(["date", "store_id"]).itertuples(index=False):
        day_meta = calendar_lookup[row.date]
        store_size = store_size_map.get(row.store_id, "Small")
        base_visits = np.random.randint(120, 250) if store_size == "Large" else np.random.randint(70, 160) if store_size == "Medium" else np.random.randint(30, 90)
        if day_meta["is_weekend"]: base_visits *= 1.15
        if day_meta["is_holiday"]: base_visits *= 1.20
        if day_meta["month"] == 12: base_visits *= 1.12
        promo_boost = row.promo_items * np.random.uniform(0.8, 2.0)
        sales_signal = row.total_units_sold * np.random.uniform(0.2, 0.8)
        friction_penalty = row.stockout_items * np.random.uniform(0.2, 0.8) + row.active_restrictions * np.random.uniform(0.1, 0.5)
        active_customers = max(5, int(base_visits + promo_boost + sales_signal - friction_penalty))
        prev_active = prior_active.get(row.store_id, active_customers)
        new_customers = max(0, int(active_customers * np.random.uniform(0.10, 0.28)))
        returning_customers = max(0, active_customers - new_customers)
        churn_risk_customers = max(0, int(row.stockout_items * np.random.uniform(0.3, 1.3)))
        net_customer_change = active_customers - prev_active
        prior_active[row.store_id] = active_customers
        rows.append({
            "date": row.date,
            "store_id": row.store_id,
            "active_customers": active_customers,
            "new_customers": new_customers,
            "returning_customers": returning_customers,
            "churn_risk_customers": churn_risk_customers,
            "net_customer_change": net_customer_change,
            "estimated_conversion_rate": round(row.total_units_sold / max(active_customers, 1), 3),
            "daily_revenue": round(row.total_revenue, 2),
        })
    return pd.DataFrame(rows), prior_active


def generate_store_operations(customer_activity_df, stores_df, calendar_df, policy_regimes_for_logic_df):
    rows = []
    customer_activity_df = customer_activity_df.copy()
    customer_activity_df["date"] = pd.to_datetime(customer_activity_df["date"])
    calendar_df = calendar_df.copy()
    calendar_df["date"] = pd.to_datetime(calendar_df["date"])
    if policy_regimes_for_logic_df is None:
        policy_regimes_for_logic_df = pd.DataFrame()
    policy_regimes_for_logic_df = policy_regimes_for_logic_df.copy()
    if not policy_regimes_for_logic_df.empty:
        policy_regimes_for_logic_df["start_date"] = pd.to_datetime(policy_regimes_for_logic_df["start_date"], format="mixed")
        policy_regimes_for_logic_df["end_date"] = pd.to_datetime(policy_regimes_for_logic_df["end_date"], format="mixed")

    store_meta = stores_df.set_index("store_id").to_dict(orient="index")
    calendar_lookup = calendar_df.set_index("date").to_dict(orient="index")

    for row in customer_activity_df.sort_values(["date", "store_id"]).itertuples(index=False):
        store_size = store_meta[row.store_id]["store_size"]
        store_type = store_meta[row.store_id]["store_type"]
        staff_on_duty = np.random.randint(12, 25) if store_size == "Large" else np.random.randint(7, 15) if store_size == "Medium" else np.random.randint(3, 8)
        day_meta = calendar_lookup[row.date]
        if day_meta["is_weekend"]: staff_on_duty = max(2, int(round(staff_on_duty * np.random.uniform(0.90, 1.05))))
        if day_meta["is_holiday"]: staff_on_duty = max(2, int(round(staff_on_duty * np.random.uniform(0.85, 1.00))))
        service_intensity_multiplier = 1.0
        active_policies = pd.DataFrame() if policy_regimes_for_logic_df.empty else policy_regimes_for_logic_df[(policy_regimes_for_logic_df["start_date"] <= row.date) & (policy_regimes_for_logic_df["end_date"] >= row.date)]
        for policy in active_policies.itertuples(index=False):
            store_type_match = (policy.affected_store_type is None) or (policy.affected_store_type == store_type)
            if store_type_match:
                service_intensity_multiplier *= float(policy.service_intensity_multiplier)
        support_requests = max(0, int(row.active_customers * np.random.uniform(0.08, 0.20) * service_intensity_multiplier))
        missed_interactions = max(0, int((support_requests + row.churn_risk_customers) * np.random.uniform(0.03, 0.15)))
        completed_interactions = max(0, support_requests - missed_interactions)
        service_pressure_score = round((row.active_customers + support_requests) / max(staff_on_duty, 1), 2)
        rows.append({
            "date": row.date,
            "store_id": row.store_id,
            "staff_on_duty": staff_on_duty,
            "customer_visits": row.active_customers,
            "support_requests": support_requests,
            "completed_interactions": completed_interactions,
            "missed_interactions": missed_interactions,
            "service_pressure_score": service_pressure_score,
        })
    return pd.DataFrame(rows)


# =========================================================
# 7. MAIN PIPELINE
# =========================================================

def main():
    ensure_core_schema()

    if RESET_DB:
        reset_supabase_tables()

    prior_state = load_generator_state()
    initialize_rng(prior_state)

    last_generated_date, forward_start, forward_end = get_effective_forward_window(
        user_start_date=USER_START_DATE,
        user_end_date=USER_END_DATE,
        prior_state=prior_state,
    )

    if forward_start is None:
        print("✅ No new dates to generate. Supabase is already up to date.")
        if last_generated_date is not None:
            print(f"📍 Last generated date: {pd.to_datetime(last_generated_date).date()}")
        return

    print(f"➡️ Forward generation window: {forward_start.date()} → {forward_end.date()}")

    stores_df = load_or_create_dim_from_supabase("dim_stores", lambda: generate_stores(N_STORES_EXTRA))
    products_df = load_or_create_dim_from_supabase("dim_products", lambda: generate_products(N_PRODUCTS))

    calendar_df = generate_calendar(str(forward_start.date()), str(forward_end.date()))
    weather_df = generate_weather(calendar_df, stores_df)
    promotions_df = generate_promotions(calendar_df, stores_df, products_df)
    policy_regimes_for_logic_df = load_policy_regimes_from_supabase(calendar_df)

    sales_df, inventory_df, restriction_events_df, updated_state = sales_inventory_and_restrictions_forward(
        calendar_df=calendar_df,
        stores_df=stores_df,
        products_df=products_df,
        weather_df=weather_df,
        promotions_df=promotions_df,
        policy_regimes_for_logic_df=policy_regimes_for_logic_df,
        prior_state=prior_state,
    )

    customer_activity_df, updated_prior_active = generate_customer_activity_forward(
        sales_df=sales_df,
        calendar_df=calendar_df,
        stores_df=stores_df,
        prior_active_customers=(prior_state or {}).get("prior_active_customers"),
    )

    store_operations_df = generate_store_operations(
        customer_activity_df=customer_activity_df,
        stores_df=stores_df,
        calendar_df=calendar_df,
        policy_regimes_for_logic_df=policy_regimes_for_logic_df,
    )

    upload_to_supabase(calendar_df, "dim_calendar")
    upload_to_supabase(weather_df, "fact_weather")
    upload_to_supabase(promotions_df, "fact_promotions")
    upload_to_supabase(sales_df, "fact_sales")
    upload_to_supabase(inventory_df, "fact_inventory")
    upload_to_supabase(customer_activity_df, "fact_customer_activity")
    upload_to_supabase(store_operations_df, "fact_store_operations")
    upload_to_supabase(restriction_events_df, "fact_restriction_events")

    final_state = {
        "inventory_state": updated_state["inventory_state"],
        "base_demand_map": updated_state["base_demand_map"],
        "last_restock_date": updated_state["last_restock_date"],
        "active_restrictions": updated_state["active_restrictions"],
        "prior_active_customers": updated_prior_active,
        "last_generated_date": pd.to_datetime(calendar_df["date"]).max(),
        "rng_state": np.random.get_state(),
    }

    save_generator_state(final_state)

    print("✅ Direct Supabase generation/upload complete.")
    print(f"✅ Added dates: {forward_start.date()} → {forward_end.date()}")
    print(
        "New rows - calendar:", len(calendar_df),
        "| weather:", len(weather_df),
        "| promotions:", len(promotions_df),
        "| sales:", len(sales_df),
        "| inventory:", len(inventory_df),
        "| customer_activity:", len(customer_activity_df),
        "| store_operations:", len(store_operations_df),
        "| restriction_events:", len(restriction_events_df),
    )


if __name__ == "__main__":
    main()
