import pandas as pd
from sqlalchemy import create_engine
from urllib.parse import quote_plus


# For CHI CHI
host = "YOUR_HOST" # add host
port = 5432
database = "postgres" 
user = "sfs_user"   # add user
password = quote_plus("YOUR_PASSWORD")  # add password

engine = create_engine(
    f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}",
    pool_pre_ping=True
)

df = pd.read_sql("SELECT * FROM core.fact_customer_activity LIMIT 5", engine)
print(df.head())


# host = "aws-1-eu-central-1.pooler.supabase.com"
# user = "sfs_user.ogkdfmkybqtrsglcizzt"
# password = "Chinenyennabude123"

# For MANOFx
import pandas as pd
from sqlalchemy import create_engine
from urllib.parse import quote_plus

host = "aws-1-eu-central-1.pooler.supabase.com"
port = 5432
database = "postgres"
user = "mano_ro.ogkdfmkybqtrsglcizzt"
password = quote_plus("Manofx12345")

engine = create_engine(
    f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}",
    pool_pre_ping=True
)

df = pd.read_sql("SELECT * FROM core.fact_sales LIMIT 5", engine)
print(df.head())


# host = "aws-1-eu-central-1.pooler.supabase.com"
# user = "mano_ro.ogkdfmkybqtrsglcizzt"
# password = "Manofx12345"


# Table names "core"

# e.g core.dim_stores


# dim_calendar
# dim_policy_regimes
# dim_products
# dim_stores
# fact_customer_activity
# fact_inventory
# fact_promotions
# fact_restrictions_events
# fact_sales
# fact_store_operations
# fact_weather
