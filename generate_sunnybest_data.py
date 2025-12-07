import numpy as np
import pandas as pd
from datetime import datetime

# ==============================
# CONFIG
# ==============================

np.random.seed(42)

START_DATE = "2021-01-01"
END_DATE = "2024-12-31"

N_PRODUCTS = 120

OUTPUT_DIR = "data/raw/"

# ==============================
# 1. STORES
# ==============================

stores_list = [
    {"store_id": 1, "store_name": "SunnyBest Benin Main",     "city": "Benin",     "area": "Oredo",     "region": "Edo South",  "store_type": "Mall",       "store_size": "Large"},
    {"store_id": 2, "store_name": "SunnyBest Ekpoma",         "city": "Ekpoma",    "area": "Esan West", "region": "Edo Central","store_type": "High Street","store_size": "Medium"},
    {"store_id": 3, "store_name": "SunnyBest Auchi",          "city": "Auchi",     "area": "Etsako West","region": "Edo North","store_type": "High Street","store_size": "Medium"},
    {"store_id": 4, "store_name": "SunnyBest Irrua",          "city": "Irrua",     "area": "Esan Central","region": "Edo Central","store_type": "Plaza","store_size": "Small"},
    {"store_id": 5, "store_name": "SunnyBest Igueben",        "city": "Igueben",   "area": "Igueben",  "region": "Edo Central","store_type": "High Street","store_size": "Small"},
    {"store_id": 6, "store_name": "SunnyBest Agenebode",      "city": "Agenebode", "area": "Etsako East","region": "Edo North","store_type": "Plaza","store_size": "Small"},
    {"store_id": 7, "store_name": "SunnyBest Ogwa",           "city": "Ogwa",      "area": "Esan West","region": "Edo Central","store_type": "High Street","store_size": "Small"},
]

stores_df = pd.DataFrame(stores_list)

# ==============================
# 2. PRODUCTS
# ==============================

categories = {
    "Mobile Phones": [
        "Samsung", "Apple", "Tecno", "Infinix", "Itel"
    ],
    "Laptops & Computers": [
        "HP", "Dell", "Lenovo", "Acer", "Asus"
    ],
    "Televisions": [
        "LG", "Samsung", "Hisense", "Sony"
    ],
    "Refrigerators": [
        "LG", "Hisense", "Haier Thermocool"
    ],
    "Air Conditioners": [
        "LG", "Hisense", "Panasonic"
    ],
    "Small Appliances": [
        "Binatone", "Philips", "Century"
    ],
    "Network Devices": [
        "Huawei", "ZTE", "TP-Link"
    ],
    "Accessories": [
        "Oraimo", "Anker", "Generic"
    ],
    "Telecom Services": [
        "MTN", "Glo", "Airtel", "9mobile"
    ],
}

def generate_products(n_products: int) -> pd.DataFrame:
    rows = []
    product_id = 1001

    # Approximate category distribution
    category_weights = {
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

    cat_list = list(category_weights.keys())
    weights = list(category_weights.values())

    for _ in range(n_products):
        cat = np.random.choice(cat_list, p=weights)
        brand = np.random.choice(categories[cat])

        # Price ranges per category (rough Naira ranges)
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

        # Seasonality (ACs peak in hot season, TVs in Dec, etc)
        if cat in ["Air Conditioners", "Refrigerators"]:
            is_seasonal = 1
        elif cat in ["Televisions", "Mobile Phones", "Telecom Services"]:
            is_seasonal = 1
        else:
            is_seasonal = 0

        warranty_months = np.random.choice([6, 12, 24])

        product_name = f"{brand} {cat.split()[0]} Model-{np.random.randint(100,999)}"

        rows.append({
            "product_id": product_id,
            "product_name": product_name,
            "category": cat,
            "brand": brand,
            "regular_price": regular_price,
            "cost_price": cost_price,
            "is_seasonal": is_seasonal,
            "warranty_months": warranty_months
        })
        product_id += 1

    return pd.DataFrame(rows)

products_df = generate_products(N_PRODUCTS)

# ==============================
# 3. CALENDAR
# ==============================

def generate_calendar(start_date: str, end_date: str) -> pd.DataFrame:
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    cal = pd.DataFrame({"date": dates})
    cal["year"] = cal["date"].dt.year
    cal["month"] = cal["date"].dt.month
    cal["day"] = cal["date"].dt.day
    cal["day_of_week"] = cal["date"].dt.day_name()
    cal["is_weekend"] = cal["day_of_week"].isin(["Saturday", "Sunday"])

    # Very simple Nigerian public holidays approximation
    def is_holiday(d):
        md = d.strftime("%m-%d")
        # New Year, Worker’s Day, Independence, Christmas, Boxing Day
        fixed = {"01-01", "05-01", "10-01", "12-25", "12-26"}
        if md in fixed:
            return True
        # Rough Easter / Eid approximations skipped; keep simple
        return False

    cal["is_holiday"] = cal["date"].apply(is_holiday)

    # Pay day: assume 25th of the month
    cal["is_payday"] = cal["day"] == 25

    # Seasons for Edo (very simplified)
    def season(m):
        if m in [11, 12, 1, 2]:
            return "Dry"
        elif m in [3, 4, 5, 6, 7]:
            return "Early Rainy"
        else:
            return "Late Rainy"

    cal["season"] = cal["month"].apply(season)
    return cal

calendar_df = generate_calendar(START_DATE, END_DATE)

# ==============================
# 4. WEATHER (simplified per city)
# ==============================

def generate_weather(calendar_df: pd.DataFrame, stores_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, store in stores_df.iterrows():
        city = store["city"]
        for _, row in calendar_df.iterrows():
            date = row["date"]
            m = row["month"]
            # Rough temp pattern (not accurate, just plausible)
            if m in [1, 2, 3]:
                base_temp = 30
            elif m in [4, 5, 6]:
                base_temp = 29
            elif m in [7, 8, 9]:
                base_temp = 27
            else:
                base_temp = 28
            temperature = base_temp + np.random.normal(0, 1.5)

            # Simple rainfall pattern
            if m in [4, 5, 6, 7, 8, 9]:
                rainfall = max(0, np.random.normal(5, 5))  # rainy
            else:
                rainfall = max(0, np.random.normal(1, 2))  # dry

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
                "weather_condition": condition
            })
    return pd.DataFrame(rows)

weather_df = generate_weather(calendar_df, stores_df)

# ==============================
# 5. PROMOTIONS
# ==============================

def generate_promotions(calendar_df, stores_df, products_df) -> pd.DataFrame:
    rows = []

    # Potential promo days: weekends, holidays, Black Friday-like (Nov Fridays)
    cal = calendar_df.copy()
    cal["month_day"] = cal["date"].dt.strftime("%m-%d")
    cal["is_black_friday_period"] = (cal["month"] == 11) & (cal["day_of_week"] == "Friday")

    for _, day in cal.iterrows():
        date = day["date"]
        promo_probability = 0.01  # baseline

        if day["is_weekend"]:
            promo_probability += 0.02
        if day["is_holiday"]:
            promo_probability += 0.05
        if day["is_black_friday_period"]:
            promo_probability += 0.10
        if day["month"] == 12:
            promo_probability += 0.04  # Christmas sales

        if np.random.rand() < promo_probability:
            # Choose some random store-product pairs to be on promo
            n_promos = np.random.randint(3, 15)
            store_ids = np.random.choice(stores_df["store_id"], size=n_promos, replace=True)
            product_ids = np.random.choice(products_df["product_id"], size=n_promos, replace=True)

            for sid, pid in zip(store_ids, product_ids):
                promo_type = np.random.choice(
                    ["Discount", "Bundle", "Free Accessory", "Price Slash"],
                    p=[0.6, 0.15, 0.15, 0.10]
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
                    "promo_flag": 1
                })

    if rows:
        promo_df = pd.DataFrame(rows)
        promo_df.drop_duplicates(subset=["date", "store_id", "product_id"], inplace=True)
    else:
        promo_df = pd.DataFrame(columns=["date", "store_id", "product_id", "promo_type", "discount_pct", "promo_flag"])

    return promo_df

promotions_df = generate_promotions(calendar_df, stores_df, products_df)

# ==============================
# 6. SALES + INVENTORY
# ==============================

def base_demand_for_product(cat: str) -> float:
    """
    Set a rough baseline average daily demand per store.
    """
    if cat == "Mobile Phones":
        return np.random.uniform(0.5, 3.0)
    elif cat == "Laptops & Computers":
        return np.random.uniform(0.2, 1.0)
    elif cat == "Televisions":
        return np.random.uniform(0.1, 0.8)
    elif cat in ["Refrigerators", "Air Conditioners"]:
        return np.random.uniform(0.05, 0.5)
    elif cat == "Small Appliances":
        return np.random.uniform(0.5, 4.0)
    elif cat == "Network Devices":
        return np.random.uniform(0.2, 2.0)
    elif cat == "Accessories":
        return np.random.uniform(1.0, 8.0)
    elif cat == "Telecom Services":
        return np.random.uniform(5.0, 30.0)
    else:
        return np.random.uniform(0.5, 3.0)

def sales_and_inventory(calendar_df, stores_df, products_df, promotions_df) -> (pd.DataFrame, pd.DataFrame):
    rows_sales = []
    rows_inv = []

    cal = calendar_df.copy()

    # Pre-merge promotions for fast lookup
    promo_index = promotions_df.set_index(["date", "store_id", "product_id"]) if len(promotions_df) > 0 else None

    # Precompute base demand per (store, product)
    base_demand_map = {}
    for _, s in stores_df.iterrows():
        for _, p in products_df.iterrows():
            key = (s["store_id"], p["product_id"])
            base_demand_map[key] = base_demand_for_product(p["category"])

    # Iterate over all date-store-product combos
    for _, day in cal.iterrows():
        date = day["date"]
        month = day["month"]
        is_weekend = day["is_weekend"]
        is_holiday = day["is_holiday"]
        season = day["season"]

        for _, store in stores_df.iterrows():
            store_id = store["store_id"]
            city = store["city"]
            store_size = store["store_size"]

            # Weather for that date and city
            w = weather_df[(weather_df["date"] == date) & (weather_df["city"] == city)]
            if len(w) > 0:
                temp = w["temperature_c"].values[0]
                rainfall = w["rainfall_mm"].values[0]
            else:
                temp = 28
                rainfall = 2

            for _, prod in products_df.iterrows():
                product_id = prod["product_id"]
                cat = prod["category"]
                regular_price = prod["regular_price"]

                # --- Base demand ---
                base = base_demand_map[(store_id, product_id)]

                # --- Store size effect ---
                if store_size == "Large":
                    base *= 1.4
                elif store_size == "Medium":
                    base *= 1.1
                else:
                    base *= 0.9

                # --- Seasonality ---
                # ACs and fridges in hotter months / dry season
                if cat in ["Air Conditioners", "Refrigerators"]:
                    if season == "Dry":
                        base *= 1.4
                # TVs & Telecom spike in Dec
                if cat in ["Televisions", "Telecom Services"] and month == 12:
                    base *= 1.5
                # Phones & accessories small uplift around festive periods
                if cat in ["Mobile Phones", "Accessories"] and month in [9, 12]:
                    base *= 1.2

                # Weekend / holiday effect
                if is_weekend:
                    base *= 1.15
                if is_holiday:
                    base *= 1.3

                # Weather effect (very rough)
                if cat == "Air Conditioners" and temp > 30:
                    base *= 1.3
                if cat == "Telecom Services" and rainfall > 5:
                    base *= 1.1  # more people at home using data

                # --- Promotion effect + price ---
                discount_pct = 0
                promo_flag = 0
                promo_type = None

                if promo_index is not None and (date, store_id, product_id) in promo_index.index:
                    promo_row = promo_index.loc[(date, store_id, product_id)]
                    if isinstance(promo_row, pd.DataFrame):
                        promo_row = promo_row.iloc[0]
                    promo_flag = 1
                    promo_type = promo_row["promo_type"]
                    discount_pct = promo_row["discount_pct"]

                # Price with discount
                price = regular_price * (1 - discount_pct / 100.0)

                # Price elasticity: if big discount, demand increases
                if discount_pct > 0:
                    elasticity_factor = 1 + (discount_pct / 50.0)  # 10% -> 1.2, 30% -> 1.6 approx
                    base *= elasticity_factor

                # --- Random noise ---
                demand_mean = base
                demand = max(0, np.random.normal(demand_mean, demand_mean * 0.3))

                # --- Inventory & stockout ---
                # approximate starting inventory around 7–21 days of mean demand
                                # --- Inventory & stockout (UPDATED) ---

                # Base stockout probability by category
                if cat in ["Mobile Phones", "Network Devices", "Accessories", "Telecom Services"]:
                    base_stockout_prob = 0.12  # higher turnover items
                else:
                    base_stockout_prob = 0.05  # lower, but still possible

                # Typical stock level: ~2–6 days of mean demand (tighter, more realistic)
                if demand_mean > 0:
                    low_stock = max(1, int(demand_mean * 1.5))
                    high_stock = max(low_stock + 1, int(demand_mean * 6))
                else:
                    low_stock, high_stock = 1, 10

                starting_inventory = np.random.randint(low_stock, high_stock)

                # Expected demand for the day
                potential_sales = max(0, int(round(demand)))

                # Random chance to deliberately under-stock (simulate supply issues)
                random_stockout = np.random.rand() < base_stockout_prob

                if random_stockout and potential_sales > 0:
                    # Force a situation where demand > inventory
                    starting_inventory = max(
                        1, int(potential_sales * np.random.uniform(0.3, 0.8))
                    )

                # Units sold limited by inventory
                units_sold = min(starting_inventory, potential_sales)
                ending_inventory = starting_inventory - units_sold
                stockout_flag = int(units_sold < potential_sales)


                revenue = units_sold * price

                # --- Save sales row ---
                rows_sales.append({
                    "date": date,
                    "store_id": store_id,
                    "product_id": product_id,
                    "units_sold": units_sold,
                    "price": round(price, 2),
                    "regular_price": regular_price,
                    "discount_pct": discount_pct,
                    "promo_flag": promo_flag,
                    "promo_type": promo_type,
                    "revenue": round(revenue, 2),
                    "starting_inventory": starting_inventory,
                    "ending_inventory": ending_inventory,
                    "stockout_occurred": stockout_flag,
                    "city": city,
                    "store_size": store_size,
                    "category": cat
                })

                # --- Save inventory row (explicit table) ---
                rows_inv.append({
                    "date": date,
                    "store_id": store_id,
                    "product_id": product_id,
                    "starting_inventory": starting_inventory,
                    "ending_inventory": ending_inventory,
                    "stockout_flag": stockout_flag
                })

    sales_df = pd.DataFrame(rows_sales)
    inventory_df = pd.DataFrame(rows_inv)

    return sales_df, inventory_df

sales_df, inventory_df = sales_and_inventory(calendar_df, stores_df, products_df, promotions_df)

# ==============================
# 7. SAVE ALL DATASETS
# ==============================

import os
os.makedirs(OUTPUT_DIR, exist_ok=True)

stores_df.to_csv(os.path.join(OUTPUT_DIR, "sunnybest_stores.csv"), index=False)
products_df.to_csv(os.path.join(OUTPUT_DIR, "sunnybest_products.csv"), index=False)
calendar_df.to_csv(os.path.join(OUTPUT_DIR, "sunnybest_calendar.csv"), index=False)
weather_df.to_csv(os.path.join(OUTPUT_DIR, "sunnybest_weather.csv"), index=False)
promotions_df.to_csv(os.path.join(OUTPUT_DIR, "sunnybest_promotions.csv"), index=False)
sales_df.to_csv(os.path.join(OUTPUT_DIR, "sunnybest_sales.csv"), index=False)
inventory_df.to_csv(os.path.join(OUTPUT_DIR, "sunnybest_inventory.csv"), index=False)

print("✅ Generated SunnyBest datasets in:", OUTPUT_DIR)
print("Rows - stores:", len(stores_df),
      "| products:", len(products_df),
      "| sales:", len(sales_df))
