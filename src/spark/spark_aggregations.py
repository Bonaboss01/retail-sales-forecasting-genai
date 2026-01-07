from pyspark.sql import DataFrame
from pyspark.sql.functions import col, sum as spark_sum

def revenue_by_category(df: DataFrame) -> DataFrame:
    return (
        df.groupBy("category")
          .agg(spark_sum(col("revenue")).alias("total_revenue"))
          .orderBy(col("total_revenue").desc())
    )
