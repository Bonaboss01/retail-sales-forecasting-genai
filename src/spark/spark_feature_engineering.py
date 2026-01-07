from pyspark.sql import DataFrame
from pyspark.sql.functions import col

def basic_feature_table(df: DataFrame) -> DataFrame:
    """
    Minimal example feature table. Extend as needed.
    """
    keep = ["date", "store_id", "product_id", "category", "price", "units_sold", "revenue", "is_weekend", "is_holiday", "season"]
    existing = [c for c in keep if c in df.columns]
    return df.select(*existing)
