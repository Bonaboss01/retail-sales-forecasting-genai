import sys
import os
import pickle
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

# =========================================================
# CONFIG
# =========================================================

SEED = 42

SCALE_MODE = os.getenv("SCALE_MODE", "small").lower()
print(f"🔧 Running SunnyBest generator in SCALE_MODE={SCALE_MODE}")

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
OUTPUT_DIR = "data/raw/"
SAVE_FORMAT = "csv"
STATE_DIR = "data/state/"
STATE_FILE = "sunnybest_generator_state.pkl"

if SCALE_MODE == "large":
    if len(sys.argv) < 3:
        USER_START_DATE = "2018-01-01"
        USER_END_DATE = datetime.today().strftime("%Y-%m-%d")
    N_PRODUCTS = 800
    N_STORES_EXTRA = 43
    OUTPUT_DIR = "data/processed/"
    SAVE_FORMAT = "parquet"

# =========================================================
# HELPERS
# =========================================================

def get_dataset_path(output_dir: str, name: str, save_format: str) -> Path:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    return Path(output_dir) / f"{name}.{save_format}"


def save_df(df: pd.DataFrame, output_dir: str, name: str, save_format: str):
    path = get_dataset_path(output_dir, name, save_format)
    if save_format == "parquet":
        df.to_parquet(path, index=False)
    else:
        df.to_csv(path, index=False)
    return path


def load_df(output_dir: str, name: str, save_format: str) -> pd.DataFrame | None:
    path = get_dataset_path(output_dir, name, save_format)
    if not path.exists():
        return None

    if save_format == "parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def append_df(
    new_df: pd.DataFrame,
    output_dir: str,
    name: str,
    save_format: str,
    dedupe_subset: list[str] | None = None,
):
    path = get_dataset_path(output_dir, name, save_format)
    existing_df = load_df(output_dir, name, save_format)

    if existing_df is None:
        combined = new_df.copy()
    else:
        combined = pd.concat([existing_df, new_df], ignore_index=True)

    if dedupe_subset:
        combined = combined.drop_duplicates(subset=dedupe_subset, keep="last").reset_index(drop=True)

    if "date" in combined.columns:
        combined["date"] = pd.to_datetime(combined["date"])
        combined = combined.sort_values(["date"] + [c for c in combined.columns if c != "date"]).reset_index(drop=True)

    save_df(combined, output_dir, name, save_format)
    return combined


def weighted_choice(options, probs):
    return np.random.choice(options, p=probs)


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


def initialize_rng(prior_state: dict | None):
    if prior_state and "rng_state" in prior_state:
        np.random.set_state(prior_state["rng_state"])
        print("🎲 Restored numpy RNG state from prior run.")
    else:
        np.random.seed(SEED)
        print(f"🎲 Initialized numpy RNG with seed={SEED}.")


def get_effective_forward_window(
    user_start_date: str,
    user_end_date: str,
    prior_state: dict | None,
):
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
    """
    Convert keys loaded from pickle or fallback sources into tuple keys.
    """
    if isinstance(k, tuple):
        return k
    if isinstance(k, str):
        parts = k.strip("()").split(",")
        if len(parts) == 2:
            return int(parts[0]), int(parts[1])
    return k


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

    extra_df = pd.DataFrame(extra_rows)
    return pd.concat([base, extra_df], ignore_index=True)


def get_or_create_stores():
    existing = load_df(OUTPUT_DIR, "sunnybest_stores", SAVE_FORMAT)
    if existing is not None and len(existing) > 0:
        print("🏬 Loaded existing stores dataset.")
        return existing

    stores_df = generate_stores(N_STORES_EXTRA)
    save_df(stores_df, OUTPUT_DIR, "sunnybest_stores", SAVE_FORMAT)
    print("🏬 Generated and saved stores dataset.")
    return stores_df


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
            regular_price = np.random.randint(70000, 550000)
        elif cat == "Laptops & Computers":
            regular_price = np.random.randint(150000, 900000)
        elif cat == "Televisions":
            regular_price = np.random.randint(80000, 700000)
        elif cat in ["Refrigerators", "Air Conditioners"]:
            regular_price = np.random.randint(100000, 850000)
        elif cat == "Small Appliances":
            regular_price = np.random.randint(15000, 80000)
        elif cat == "Network Devices":
            regular_price = np.random.randint(20000, 120000)
        elif cat == "Accessories":
            regular_price = np.random.randint(5000, 40000)
        elif cat == "Telecom Services":
            regular_price = np.random.randint(500, 20000)
        else:
            regular_price = np.random.randint(10000, 500000)

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


def get_or_create_products():
    existing = load_df(OUTPUT_DIR, "sunnybest_products", SAVE_FORMAT)
    if existing is not None and len(existing) > 0:
        print("📦 Loaded existing products dataset.")
        return existing

    products_df = generate_products(N_PRODUCTS)
    save_df(products_df, OUTPUT_DIR, "sunnybest_products", SAVE_FORMAT)
    print("📦 Generated and saved products dataset.")
    return products_df


# =========================================================
# 3. CALENDAR
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

    def is_holiday(d):
        return d.strftime("%m-%d") in fixed_holidays

    def season(m):
        if m in [11, 12, 1, 2]:
            return "Dry"
        elif m in [3, 4, 5, 6, 7]:
            return "Early Rainy"
        return "Late Rainy"

    cal["is_holiday"] = cal["date"].apply(is_holiday)
    cal["is_payday"] = cal["day"] == 25
    cal["season"] = cal["month"].apply(season)
    cal["is_black_friday_period"] = (cal["month"] == 11) & (cal["day_of_week"] == "Friday")
    return cal


# =========================================================
# 4. WEATHER
# =========================================================

def generate_weather(calendar_df: pd.DataFrame, stores_df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for _, store in stores_df.iterrows():
        city = store["city"]
        for _, day in calendar_df.iterrows():
            date = day["date"]
            month = day["month"]

            if month in [1, 2, 3]:
                base_temp = 30
            elif month in [4, 5, 6]:
                base_temp = 29
            elif month in [7, 8, 9]:
                base_temp = 27
            else:
                base_temp = 28

            temperature = base_temp + np.random.normal(0, 1.5)

            if month in [4, 5, 6, 7, 8, 9]:
                rainfall = max(0, np.random.normal(5, 5))
            else:
                rainfall = max(0, np.random.normal(1, 2))

            if rainfall == 0:
                condition = "Sunny"
            elif rainfall < 3:
                condition = "Cloudy"
            else:
                condition = "Rainy"

            rows.append({
                "date": date,
                "city": city,
                "temperature_c": round(temperature, 1),
                "rainfall_mm": round(rainfall, 1),
                "weather_condition": condition,
            })

    return pd.DataFrame(rows)


# =========================================================
# 5. PROMOTIONS
# =========================================================

def generate_promotions(calendar_df: pd.DataFrame, stores_df: pd.DataFrame, products_df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for _, day in calendar_df.iterrows():
        date = day["date"]
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
                promo_type = np.random.choice(
                    ["Discount", "Bundle", "Free Accessory", "Price Slash"],
                    p=[0.6, 0.15, 0.15, 0.10],
                )
                discount_pct = 0
                if promo_type in ["Discount", "Price Slash"]:
                    discount_pct = np.random.choice([5, 10, 15, 20, 25, 30])

                rows.append({
                    "date": date,
                    "store_id": int(sid),
                    "product_id": int(pid),
                    "promo_type": promo_type,
                    "discount_pct": discount_pct,
                    "promo_flag": 1,
                })

    if not rows:
        return pd.DataFrame(columns=["date", "store_id", "product_id", "promo_type", "discount_pct", "promo_flag"])

    promo_df = pd.DataFrame(rows)
    promo_df = promo_df.drop_duplicates(subset=["date", "store_id", "product_id"]).reset_index(drop=True)
    return promo_df


# =========================================================
# 6. POLICY REGIMES
# =========================================================

def generate_policy_regimes(calendar_df: pd.DataFrame) -> pd.DataFrame:
    min_date = calendar_df["date"].min()
    max_date = calendar_df["date"].max()

    candidate_policies = [
        {
            "policy_name": "Telecom Seasonal Push",
            "affected_category": "Telecom Services",
            "affected_store_type": None,
            "demand_multiplier": 1.15,
            "discount_cap_pct": 20,
            "replenishment_multiplier": 1.10,
            "service_intensity_multiplier": 1.08,
        },
        {
            "policy_name": "Premium Electronics Margin Protection",
            "affected_category": "Mobile Phones",
            "affected_store_type": None,
            "demand_multiplier": 0.96,
            "discount_cap_pct": 10,
            "replenishment_multiplier": 0.95,
            "service_intensity_multiplier": 1.02,
        },
        {
            "policy_name": "Mall Expansion Drive",
            "affected_category": None,
            "affected_store_type": "Mall",
            "demand_multiplier": 1.08,
            "discount_cap_pct": 25,
            "replenishment_multiplier": 1.12,
            "service_intensity_multiplier": 1.10,
        },
        {
            "policy_name": "Small Store Inventory Control",
            "affected_category": None,
            "affected_store_type": "Plaza",
            "demand_multiplier": 0.98,
            "discount_cap_pct": 15,
            "replenishment_multiplier": 0.88,
            "service_intensity_multiplier": 1.00,
        },
        {
            "policy_name": "Cooling Appliances Availability Programme",
            "affected_category": "Air Conditioners",
            "affected_store_type": None,
            "demand_multiplier": 1.10,
            "discount_cap_pct": 20,
            "replenishment_multiplier": 1.20,
            "service_intensity_multiplier": 1.05,
        },
    ]

    n_policies = min(4, len(candidate_policies))
    selected = np.random.choice(len(candidate_policies), size=n_policies, replace=False)

    windows = []
    total_days = max(1, (max_date - min_date).days)

    for i, idx in enumerate(selected, start=1):
        policy = candidate_policies[idx]
        start_offset = np.random.randint(0, max(1, total_days))
        duration = np.random.randint(90, 240)
        start_date = min_date + pd.Timedelta(days=int(start_offset))
        end_date = min(start_date + pd.Timedelta(days=int(duration)), max_date)

        windows.append({
            "policy_id": i,
            "policy_name": policy["policy_name"],
            "start_date": start_date,
            "end_date": end_date,
            "affected_category": policy["affected_category"],
            "affected_store_type": policy["affected_store_type"],
            "demand_multiplier": policy["demand_multiplier"],
            "discount_cap_pct": policy["discount_cap_pct"],
            "replenishment_multiplier": policy["replenishment_multiplier"],
            "service_intensity_multiplier": policy["service_intensity_multiplier"],
        })

    return pd.DataFrame(windows)


def get_policy_regimes_for_current_window(calendar_df: pd.DataFrame):
    existing = load_df(OUTPUT_DIR, "sunnybest_policy_regimes", SAVE_FORMAT)
    new_policies = generate_policy_regimes(calendar_df)

    if existing is None or len(existing) == 0:
        policies_for_logic = new_policies.copy()
    else:
        existing["start_date"] = pd.to_datetime(existing["start_date"], format="mixed")
        existing["end_date"] = pd.to_datetime(existing["end_date"], format = "mixed")
        window_start = pd.to_datetime(calendar_df["date"].min())
        window_end = pd.to_datetime(calendar_df["date"].max())

        overlapping_existing = existing[
            (existing["start_date"] <= window_end) &
            (existing["end_date"] >= window_start)
        ].copy()

        policies_for_logic = pd.concat([overlapping_existing, new_policies], ignore_index=True)

    return new_policies, policies_for_logic


# =========================================================
# 7. BASE DEMAND
# =========================================================

def base_demand_for_category(category: str) -> float:
    if category == "Mobile Phones":
        return np.random.uniform(0.5, 3.0)
    if category == "Laptops & Computers":
        return np.random.uniform(0.2, 1.0)
    if category == "Televisions":
        return np.random.uniform(0.1, 0.8)
    if category in ["Refrigerators", "Air Conditioners"]:
        return np.random.uniform(0.05, 0.5)
    if category == "Small Appliances":
        return np.random.uniform(0.5, 4.0)
    if category == "Network Devices":
        return np.random.uniform(0.2, 2.0)
    if category == "Accessories":
        return np.random.uniform(1.0, 8.0)
    if category == "Telecom Services":
        return np.random.uniform(5.0, 30.0)
    return np.random.uniform(0.5, 3.0)


def target_inventory_days(category: str) -> tuple[int, int]:
    if category in ["Mobile Phones", "Network Devices", "Accessories", "Telecom Services"]:
        return 4, 10
    if category in ["Laptops & Computers", "Televisions"]:
        return 6, 14
    if category in ["Refrigerators", "Air Conditioners"]:
        return 7, 16
    return 5, 12


def base_stockout_probability(category: str) -> float:
    if category in ["Mobile Phones", "Network Devices", "Accessories", "Telecom Services"]:
        return 0.08
    if category in ["Laptops & Computers", "Televisions"]:
        return 0.05
    return 0.03


def restock_frequency_days(store_size: str) -> int:
    if store_size == "Large":
        return 3
    if store_size == "Medium":
        return 5
    return 7


# =========================================================
# 8. SALES + INVENTORY + RESTRICTIONS (FORWARD ONLY)
# =========================================================

def sales_inventory_and_restrictions_forward(
    calendar_df: pd.DataFrame,
    stores_df: pd.DataFrame,
    products_df: pd.DataFrame,
    weather_df: pd.DataFrame,
    promotions_df: pd.DataFrame,
    policy_regimes_for_logic_df: pd.DataFrame,
    prior_state: dict | None = None,
):
    rows_sales = []
    rows_inventory = []
    rows_restrictions = []

    weather_lookup = {
        (pd.to_datetime(row.date), row.city): (row.temperature_c, row.rainfall_mm, row.weather_condition)
        for row in weather_df.itertuples(index=False)
    }

    promo_lookup = {
        (pd.to_datetime(row.date), row.store_id, row.product_id): {
            "promo_type": row.promo_type,
            "discount_pct": row.discount_pct,
            "promo_flag": row.promo_flag,
        }
        for row in promotions_df.itertuples(index=False)
    }

    if prior_state is None:
        inventory_state = {}
        base_demand_map = {}
        last_restock_date = {}
        active_restrictions = {}
        print("🆕 No prior state found. Initializing generator from scratch.")
    else:
        inventory_state = {parse_key(k): v for k, v in prior_state.get("inventory_state", {}).items()}
        base_demand_map = {parse_key(k): v for k, v in prior_state.get("base_demand_map", {}).items()}
        last_restock_date = {parse_key(k): pd.to_datetime(v) for k, v in prior_state.get("last_restock_date", {}).items()}
        active_restrictions = {parse_key(k): v for k, v in prior_state.get("active_restrictions", {}).items()}

        for k, v in active_restrictions.items():
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
                start_days = np.random.randint(low_days, high_days + 1)
                starting_inventory = max(1, int(round(base_demand_map[key] * start_days)))
                inventory_state[key] = starting_inventory

            if key not in last_restock_date:
                last_restock_date[key] = pd.to_datetime(calendar_df["date"].min()) - pd.Timedelta(days=np.random.randint(1, 7))

    all_dates = sorted(pd.to_datetime(calendar_df["date"]).tolist())

    for current_date in all_dates:
        day = calendar_df.loc[pd.to_datetime(calendar_df["date"]) == current_date].iloc[0]
        month = int(day["month"])
        is_weekend = bool(day["is_weekend"])
        is_holiday = bool(day["is_holiday"])
        season = day["season"]

        expired_keys = []
        for r_key, r_info in active_restrictions.items():
            if current_date > pd.to_datetime(r_info["end_date"]):
                expired_keys.append(r_key)
        for e_key in expired_keys:
            del active_restrictions[e_key]

        active_policies_today = policy_regimes_for_logic_df[
            (pd.to_datetime(policy_regimes_for_logic_df["start_date"]) <= current_date) &
            (pd.to_datetime(policy_regimes_for_logic_df["end_date"]) >= current_date)
        ]

        for store in stores_df.itertuples(index=False):
            store_id = store.store_id
            city = store.city
            store_size = store.store_size
            store_type = store.store_type

            temp, rainfall, _condition = weather_lookup.get((current_date, city), (28.0, 2.0, "Cloudy"))

            for product in products_df.itertuples(index=False):
                product_id = product.product_id
                category = product.category
                regular_price = product.regular_price

                sp_key = (store_id, product_id)
                current_inventory = inventory_state[sp_key]

                days_since_restock = (current_date - pd.to_datetime(last_restock_date[sp_key])).days
                restock_every = restock_frequency_days(store_size)

                replenishment_multiplier = 1.0
                applicable_discount_cap = 30

                for policy in active_policies_today.itertuples(index=False):
                    category_match = (policy.affected_category is None) or (policy.affected_category == category)
                    store_type_match = (policy.affected_store_type is None) or (policy.affected_store_type == store_type)

                    if category_match and store_type_match:
                        replenishment_multiplier *= float(policy.replenishment_multiplier)
                        applicable_discount_cap = min(applicable_discount_cap, int(policy.discount_cap_pct))

                active_restriction = active_restrictions.get(sp_key)
                restriction_type = None
                restriction_reason = None
                restriction_severity = None
                restriction_active_flag = 0
                restriction_multiplier_demand = 1.0
                restriction_multiplier_replenishment = 1.0

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
                    desired_stock = max(
                        1,
                        int(round(base_demand_map[sp_key] * target_days * replenishment_multiplier * restriction_multiplier_replenishment))
                    )
                    if desired_stock > current_inventory:
                        restock_qty = desired_stock - current_inventory
                        current_inventory += restock_qty
                    last_restock_date[sp_key] = current_date

                base = base_demand_map[sp_key]

                if store_size == "Large":
                    base *= 1.4
                elif store_size == "Medium":
                    base *= 1.1
                else:
                    base *= 0.9

                if category in ["Air Conditioners", "Refrigerators"] and season == "Dry":
                    base *= 1.4
                if category in ["Televisions", "Telecom Services"] and month == 12:
                    base *= 1.5
                if category in ["Mobile Phones", "Accessories"] and month in [9, 12]:
                    base *= 1.2

                if is_weekend:
                    base *= 1.15
                if is_holiday:
                    base *= 1.3
                if category == "Air Conditioners" and temp > 30:
                    base *= 1.3
                if category == "Telecom Services" and rainfall > 5:
                    base *= 1.1

                for policy in active_policies_today.itertuples(index=False):
                    category_match = (policy.affected_category is None) or (policy.affected_category == category)
                    store_type_match = (policy.affected_store_type is None) or (policy.affected_store_type == store_type)
                    if category_match and store_type_match:
                        base *= float(policy.demand_multiplier)

                base *= restriction_multiplier_demand

                promo = promo_lookup.get((current_date, store_id, product_id), None)
                promo_flag = 0
                promo_type = None
                discount_pct = 0

                if promo:
                    promo_flag = int(promo["promo_flag"])
                    promo_type = promo["promo_type"]
                    discount_pct = min(int(promo["discount_pct"]), applicable_discount_cap)

                price = regular_price * (1 - discount_pct / 100.0)

                if discount_pct > 0:
                    elasticity_factor = 1 + (discount_pct / 50.0)
                    base *= elasticity_factor

                demand_mean = max(0.01, base)
                raw_demand = max(0, np.random.normal(demand_mean, demand_mean * 0.3))
                potential_sales = max(0, int(round(raw_demand)))

                supply_issue_triggered = np.random.rand() < base_stockout_probability(category)

                if supply_issue_triggered and sp_key not in active_restrictions and np.random.rand() < 0.25:
                    new_type = weighted_choice(
                        ["Stock Restriction", "Supply Delay", "Promo Suspension", "Category Cap"],
                        [0.45, 0.30, 0.15, 0.10]
                    )
                    new_severity = weighted_choice(["Low", "Medium", "High"], [0.5, 0.35, 0.15])

                    if new_type == "Stock Restriction":
                        new_reason = "Low available inventory"
                        demand_mult = 0.92
                        replen_mult = 0.70
                    elif new_type == "Supply Delay":
                        new_reason = "Replenishment delay"
                        demand_mult = 0.97
                        replen_mult = 0.60
                    elif new_type == "Promo Suspension":
                        new_reason = "Margin protection rule"
                        demand_mult = 0.90
                        replen_mult = 1.00
                    else:
                        new_reason = "Category-level control"
                        demand_mult = 0.88
                        replen_mult = 0.85

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

                    restriction_type = new_type
                    restriction_reason = new_reason
                    restriction_severity = new_severity
                    restriction_active_flag = 1

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
                    promo_flag = 0
                    promo_type = None
                    discount_pct = 0
                    price = regular_price

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

    sales_df = pd.DataFrame(rows_sales)
    inventory_df = pd.DataFrame(rows_inventory)

    if rows_restrictions:
        restriction_events_df = pd.DataFrame(rows_restrictions)
    else:
        restriction_events_df = pd.DataFrame(columns=[
            "date", "store_id", "product_id", "restriction_type",
            "restriction_reason", "restriction_severity", "duration_days", "active_flag"
        ])

    updated_state = {
        "inventory_state": inventory_state,
        "base_demand_map": base_demand_map,
        "last_restock_date": {k: pd.to_datetime(v) for k, v in last_restock_date.items()},
        "active_restrictions": active_restrictions,
    }

    return sales_df, inventory_df, restriction_events_df, updated_state


# =========================================================
# 9. CUSTOMER ACTIVITY (FORWARD ONLY)
# =========================================================

def generate_customer_activity_forward(
    sales_df: pd.DataFrame,
    calendar_df: pd.DataFrame,
    stores_df: pd.DataFrame,
    prior_active_customers: dict | None = None,
):
    rows = []

    daily_store_sales = (
        sales_df.groupby(["date", "store_id"], as_index=False)
        .agg(
            total_units_sold=("units_sold", "sum"),
            total_revenue=("revenue", "sum"),
            promo_items=("promo_flag", "sum"),
            stockout_items=("stockout_occurred", "sum"),
            active_restrictions=("restriction_active", "sum"),
        )
    )

    daily_store_sales["date"] = pd.to_datetime(daily_store_sales["date"])
    calendar_df = calendar_df.copy()
    calendar_df["date"] = pd.to_datetime(calendar_df["date"])

    calendar_lookup = calendar_df.set_index("date").to_dict(orient="index")
    store_size_map = stores_df.set_index("store_id")["store_size"].to_dict()

    if prior_active_customers is None:
        prior_active = {}
    else:
        prior_active = {int(k): int(v) for k, v in prior_active_customers.items()}

    for row in daily_store_sales.sort_values(["date", "store_id"]).itertuples(index=False):
        date = row.date
        store_id = row.store_id
        total_units = row.total_units_sold
        total_revenue = row.total_revenue
        promo_items = row.promo_items
        stockout_items = row.stockout_items
        active_restrictions = row.active_restrictions

        day_meta = calendar_lookup[date]
        store_size = store_size_map.get(store_id, "Small")

        if store_size == "Large":
            base_visits = np.random.randint(120, 250)
        elif store_size == "Medium":
            base_visits = np.random.randint(70, 160)
        else:
            base_visits = np.random.randint(30, 90)

        if day_meta["is_weekend"]:
            base_visits *= 1.15
        if day_meta["is_holiday"]:
            base_visits *= 1.20
        if day_meta["month"] == 12:
            base_visits *= 1.12

        promo_boost = promo_items * np.random.uniform(0.8, 2.0)
        sales_signal = total_units * np.random.uniform(0.2, 0.8)
        friction_penalty = (stockout_items * np.random.uniform(0.2, 0.8)) + (active_restrictions * np.random.uniform(0.1, 0.5))

        active_customers = max(5, int(base_visits + promo_boost + sales_signal - friction_penalty))

        prev_active = prior_active.get(store_id, active_customers)
        new_customers = max(0, int(active_customers * np.random.uniform(0.10, 0.28)))
        returning_customers = max(0, active_customers - new_customers)
        churn_risk_customers = max(0, int(stockout_items * np.random.uniform(0.3, 1.3)))
        net_customer_change = active_customers - prev_active

        prior_active[store_id] = active_customers

        rows.append({
            "date": date,
            "store_id": store_id,
            "active_customers": active_customers,
            "new_customers": new_customers,
            "returning_customers": returning_customers,
            "churn_risk_customers": churn_risk_customers,
            "net_customer_change": net_customer_change,
            "estimated_conversion_rate": round(total_units / max(active_customers, 1), 3),
            "daily_revenue": round(total_revenue, 2),
        })

    return pd.DataFrame(rows), prior_active


# =========================================================
# 10. STORE OPERATIONS
# =========================================================

def generate_store_operations(
    customer_activity_df: pd.DataFrame,
    stores_df: pd.DataFrame,
    calendar_df: pd.DataFrame,
    policy_regimes_for_logic_df: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    customer_activity_df = customer_activity_df.copy()
    customer_activity_df["date"] = pd.to_datetime(customer_activity_df["date"])
    calendar_df = calendar_df.copy()
    calendar_df["date"] = pd.to_datetime(calendar_df["date"])
    policy_regimes_for_logic_df = policy_regimes_for_logic_df.copy()
    policy_regimes_for_logic_df["start_date"] = pd.to_datetime(policy_regimes_for_logic_df["start_date"])
    policy_regimes_for_logic_df["end_date"] = pd.to_datetime(policy_regimes_for_logic_df["end_date"])

    store_meta = stores_df.set_index("store_id").to_dict(orient="index")
    calendar_lookup = calendar_df.set_index("date").to_dict(orient="index")

    for row in customer_activity_df.sort_values(["date", "store_id"]).itertuples(index=False):
        store_id = row.store_id
        date = row.date
        active_customers = row.active_customers
        churn_risk = row.churn_risk_customers

        store_size = store_meta[store_id]["store_size"]
        store_type = store_meta[store_id]["store_type"]

        if store_size == "Large":
            staff_on_duty = np.random.randint(12, 25)
        elif store_size == "Medium":
            staff_on_duty = np.random.randint(7, 15)
        else:
            staff_on_duty = np.random.randint(3, 8)

        day_meta = calendar_lookup[date]
        if day_meta["is_weekend"]:
            staff_on_duty = max(2, int(round(staff_on_duty * np.random.uniform(0.90, 1.05))))
        if day_meta["is_holiday"]:
            staff_on_duty = max(2, int(round(staff_on_duty * np.random.uniform(0.85, 1.00))))

        service_intensity_multiplier = 1.0
        active_policies = policy_regimes_for_logic_df[
            (policy_regimes_for_logic_df["start_date"] <= date) &
            (policy_regimes_for_logic_df["end_date"] >= date)
        ]

        for policy in active_policies.itertuples(index=False):
            store_type_match = (policy.affected_store_type is None) or (policy.affected_store_type == store_type)
            if store_type_match:
                service_intensity_multiplier *= float(policy.service_intensity_multiplier)

        support_requests = max(0, int(active_customers * np.random.uniform(0.08, 0.20) * service_intensity_multiplier))
        missed_interactions = max(0, int((support_requests + churn_risk) * np.random.uniform(0.03, 0.15)))
        completed_interactions = max(0, support_requests - missed_interactions)
        service_pressure_score = round((active_customers + support_requests) / max(staff_on_duty, 1), 2)

        rows.append({
            "date": date,
            "store_id": store_id,
            "staff_on_duty": staff_on_duty,
            "customer_visits": active_customers,
            "support_requests": support_requests,
            "completed_interactions": completed_interactions,
            "missed_interactions": missed_interactions,
            "service_pressure_score": service_pressure_score,
        })

    return pd.DataFrame(rows)


# =========================================================
# 11. MAIN
# =========================================================

def main():
    prior_state = load_generator_state()

    sales_path = get_dataset_path(OUTPUT_DIR, "sunnybest_sales", SAVE_FORMAT)

    if prior_state is not None and not sales_path.exists():
        raise FileNotFoundError(
            "❌ Generator state exists, but sunnybest_sales file is missing. "
            "This means state and CSV data are out of sync. "
            "Delete the state file and rebuild from 2021, or restore the full CSV."
        )

    initialize_rng(prior_state)

    last_generated_date, forward_start, forward_end = get_effective_forward_window(
        user_start_date=USER_START_DATE,
        user_end_date=USER_END_DATE,
        prior_state=prior_state,
    )

    if forward_start is None:
        print("✅ No new dates to generate. Dataset is already up to date.")
        if last_generated_date is not None:
            print(f"📍 Last generated date: {pd.to_datetime(last_generated_date).date()}")
        return

    print(f"➡️ Forward generation window: {forward_start.date()} → {forward_end.date()}")

    stores_df = get_or_create_stores()
    products_df = get_or_create_products()

    calendar_df = generate_calendar(str(forward_start.date()), str(forward_end.date()))
    weather_df = generate_weather(calendar_df, stores_df)
    promotions_df = generate_promotions(calendar_df, stores_df, products_df)

    new_policy_regimes_df, policy_regimes_for_logic_df = get_policy_regimes_for_current_window(calendar_df)

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

    append_df(calendar_df, OUTPUT_DIR, "sunnybest_calendar", SAVE_FORMAT, dedupe_subset=["date"])
    append_df(weather_df, OUTPUT_DIR, "sunnybest_weather", SAVE_FORMAT, dedupe_subset=["date", "city"])
    append_df(promotions_df, OUTPUT_DIR, "sunnybest_promotions", SAVE_FORMAT, dedupe_subset=["date", "store_id", "product_id"])
    append_df(new_policy_regimes_df, OUTPUT_DIR, "sunnybest_policy_regimes", SAVE_FORMAT, dedupe_subset=["policy_name", "start_date", "end_date", "affected_category", "affected_store_type"])
    append_df(sales_df, OUTPUT_DIR, "sunnybest_sales", SAVE_FORMAT, dedupe_subset=["date", "store_id", "product_id"])
    append_df(inventory_df, OUTPUT_DIR, "sunnybest_inventory", SAVE_FORMAT, dedupe_subset=["date", "store_id", "product_id"])
    append_df(customer_activity_df, OUTPUT_DIR, "sunnybest_customer_activity", SAVE_FORMAT, dedupe_subset=["date", "store_id"])
    append_df(store_operations_df, OUTPUT_DIR, "sunnybest_store_operations", SAVE_FORMAT, dedupe_subset=["date", "store_id"])
    append_df(restriction_events_df, OUTPUT_DIR, "sunnybest_restriction_events", SAVE_FORMAT, dedupe_subset=["date", "store_id", "product_id", "restriction_type"])

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

    print("✅ Forward-only SunnyBest generation complete.")
    print(f"✅ Added dates: {forward_start.date()} → {forward_end.date()}")
    print(f"✅ Output directory: {OUTPUT_DIR}")
    print(f"✅ Format: {SAVE_FORMAT}")
    print(
        "New rows - calendar:", len(calendar_df),
        "| weather:", len(weather_df),
        "| promotions:", len(promotions_df),
        "| policy_regimes:", len(new_policy_regimes_df),
        "| sales:", len(sales_df),
        "| inventory:", len(inventory_df),
        "| customer_activity:", len(customer_activity_df),
        "| store_operations:", len(store_operations_df),
        "| restriction_events:", len(restriction_events_df),
    )


if __name__ == "__main__":
    main()