# Spark Module (Optional)

This module contains optional Spark utilities for scaling the SunnyBest pipeline.

- `spark_session.py`: creates/configures Spark sessions
- `spark_etl.py`: reads raw data and produces curated tables
- `spark_aggregations.py`: business aggregates (daily revenue, category revenue, etc.)
- `spark_feature_engineering.py`: feature tables for modelling

At the current project scale, pandas is sufficient. Spark is included to demonstrate how this pipeline would scale in production.
