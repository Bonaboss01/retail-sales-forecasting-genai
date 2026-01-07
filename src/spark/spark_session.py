from pyspark.sql import SparkSession

def get_spark(app_name: str = "SunnyBest-Spark") -> SparkSession:
    """
    Create and return a Spark session.
    """
    spark = (
        SparkSession.builder
        .appName(app_name)
        .getOrCreate()
    )
    return spark
