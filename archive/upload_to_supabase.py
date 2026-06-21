import pandas as pd
from sqlalchemy import create_engine

# Replace with your real Supabase connection string
SUPABASE_DB_URL = "postgresql://postgres:Bonabosssfs01@db.ogkdfmkybqtrsglcizzt.supabase.co:5432/postgres"

engine = create_engine(SUPABASE_DB_URL)

files = {
    "dim_calendar": "data/raw/sunnybest_calendar.csv",
    "fact_customer_activity": "data/raw/sunnybest_customer_activity.csv",
    "fact_inventory": "data/raw/sunnybest_inventory.csv",
    "dim_policy_regimes": "data/raw/sunnybest_policy_regimes.csv",
    "dim_products": "data/raw/sunnybest_products.csv",
    "fact_promotions": "data/raw/sunnybest_promotions.csv",
    "fact_restriction_events": "data/raw/sunnybest_restriction_events.csv",
    "fact_sales": "data/raw/sunnybest_sales.csv",
    "fact_store_operations": "data/raw/sunnybest_store_operations.csv",
    "dim_stores": "data/raw/sunnybest_stores.csv",
    "fact_weather": "data/raw/sunnybest_weather.csv",
}

for table_name, file_path in files.items():
    print(f"Uploading {file_path} -> core.{table_name}")

    df = pd.read_csv(file_path, low_memory=False)
    print(f"{table_name}: {len(df):,} rows")

    if table_name == "fact_sales" and len(df) < 1_600_000:
        raise ValueError(
            f"❌ Upload blocked: core.fact_sales has only {len(df):,} rows. "
            "Expected around 1.6M + rows of Sales . Upload stopped to prevent data loss."
        )

    df.to_sql(
        name=table_name,
        con=engine,
        schema="core",
        if_exists="replace",
        index=False
    )

    print(f"Done: core.{table_name}")

print("All files uploaded successfully.")