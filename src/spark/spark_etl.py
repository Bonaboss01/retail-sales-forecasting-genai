from pyspark.sql import DataFrame
from pyspark.sql.functions import col

def load_raw(spark, raw_dir: str):
    sales = spark.read.csv(f"{raw_dir}/sunnybest_sales.csv", header=True, inferSchema=True)
    products = spark.read.csv(f"{raw_dir}/sunnybest_products.csv", header=True, inferSchema=True)
    stores = spark.read.csv(f"{raw_dir}/sunnybest_stores.csv", header=True, inferSchema=True)
    calendar = spark.read.csv(f"{raw_dir}/sunnybest_calendar.csv", header=True, inferSchema=True)
    return sales, products, stores, calendar

def build_enriched_table(sales: DataFrame, products: DataFrame, stores: DataFrame, calendar: DataFrame) -> DataFrame:
    """
    Spark equivalent of pandas merge: enrich sales with product/store/calendar attributes.
    """
    df = (
        sales
        .join(products, on="product_id", how="left")
        .join(stores, on="store_id", how="left")
        .join(calendar, on="date", how="left")
    )
    return df
