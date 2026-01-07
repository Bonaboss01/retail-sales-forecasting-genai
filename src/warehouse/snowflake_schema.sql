-- Example Snowflake schema (conceptual)
CREATE SCHEMA IF NOT EXISTS SUNNYBEST_ANALYTICS;

CREATE OR REPLACE TABLE SUNNYBEST_ANALYTICS.STG_SALES_ENRICHED (
  date DATE,
  store_id INTEGER,
  product_id INTEGER,
  category STRING,
  price FLOAT,
  units_sold INTEGER,
  revenue FLOAT
);
