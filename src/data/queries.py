"""
Pre-built SQL queries for common SunnyBest data joins.
Use these instead of writing raw SQL in every script.

Usage:
    from src.data.queries import fetch_sales_with_context
"""

import pandas as pd
from src.data.db_connection import run_query


def fetch_sales_with_context(limit: int | None = None) -> "pd.DataFrame":
    """
    fact_sales joined with stores, products, calendar and weather.
    This is the main analytical frame used by most models and notebooks.
    """
    query = """
        SELECT
            s.date,
            s.store_id,
            st.store_name,
            st.store_size,
            st.store_type,
            st.city,
            st.region,
            s.product_id,
            p.product_name,
            p.category,
            p.brand,
            p.regular_price,
            p.cost_price,
            s.units_sold,
            s.price,
            s.discount_pct,
            s.promo_flag,
            s.revenue,
            s.starting_inventory,
            s.ending_inventory,
            s.stockout_occurred,
            s.restriction_active,
            c.season,
            c.month,
            c.is_weekend,
            c.is_holiday,
            c.is_payday,
            w.temperature_c,
            w.rainfall_mm,
            w.weather_condition
        FROM core.fact_sales s
        LEFT JOIN core.dim_stores   st ON s.store_id   = st.store_id
        LEFT JOIN core.dim_products  p ON s.product_id  = p.product_id
        LEFT JOIN core.dim_calendar  c ON s.date        = c.date
        LEFT JOIN core.fact_weather  w ON s.date        = w.date AND st.city = w.city
    """
    if limit:
        query += f" LIMIT {limit}"
    return run_query(query)


def fetch_sales_with_promotions(limit: int | None = None) -> "pd.DataFrame":
    """
    fact_sales joined with promotions — used for promo uplift and pricing models.
    """
    query = """
        SELECT
            s.date,
            s.store_id,
            s.product_id,
            p.category,
            s.units_sold,
            s.price,
            s.regular_price,
            s.revenue,
            s.stockout_occurred,
            c.season,
            c.is_weekend,
            c.is_holiday,
            c.is_payday,
            COALESCE(pr.promo_flag,    0)    AS promo_flag,
            COALESCE(pr.discount_pct,  0)    AS discount_pct,
            pr.promo_type
        FROM core.fact_sales s
        LEFT JOIN core.dim_products  p  ON s.product_id  = p.product_id
        LEFT JOIN core.dim_calendar  c  ON s.date        = c.date
        LEFT JOIN core.fact_promotions pr
               ON s.date = pr.date
              AND s.store_id = pr.store_id
              AND s.product_id = pr.product_id
    """
    if limit:
        query += f" LIMIT {limit}"
    return run_query(query)


def fetch_inventory_with_context(limit: int | None = None) -> "pd.DataFrame":
    """
    fact_inventory joined with stores and products — used for stockout analysis.
    """
    query = """
        SELECT
            i.date,
            i.store_id,
            st.store_name,
            st.store_size,
            st.region,
            i.product_id,
            p.product_name,
            p.category,
            i.starting_inventory,
            i.restock_qty,
            i.ending_inventory,
            i.stockout_flag,
            c.season,
            c.month,
            c.is_weekend,
            c.is_payday
        FROM core.fact_inventory i
        LEFT JOIN core.dim_stores   st ON i.store_id   = st.store_id
        LEFT JOIN core.dim_products  p ON i.product_id  = p.product_id
        LEFT JOIN core.dim_calendar  c ON i.date        = c.date
    """
    if limit:
        query += f" LIMIT {limit}"
    return run_query(query)


def fetch_weekly_sales(limit: int | None = None) -> "pd.DataFrame":
    """
    Weekly aggregated sales per store × product — ready for model training.
    """
    query = """
        SELECT
            DATE_TRUNC('week', s.date)::date    AS week_start,
            EXTRACT(YEAR  FROM s.date)::int     AS year,
            EXTRACT(WEEK  FROM s.date)::int     AS week,
            EXTRACT(MONTH FROM s.date)::int     AS month,
            EXTRACT(QUARTER FROM s.date)::int   AS quarter,
            EXTRACT(DOW   FROM DATE_TRUNC('week', s.date))::int AS week_of_year,
            s.store_id,
            s.product_id,
            p.category,
            st.store_size,
            SUM(s.units_sold)                   AS units_sold,
            AVG(s.price)                        AS avg_price,
            AVG(p.regular_price)                AS avg_regular_price,
            AVG(s.discount_pct)                 AS avg_discount_pct,
            AVG(i.starting_inventory)           AS avg_starting_inventory,
            MAX(c.season)                       AS season,
            SUM(s.promo_flag)::float /
                NULLIF(COUNT(*), 0)             AS promo_intensity
        FROM core.fact_sales s
        LEFT JOIN core.dim_products   p  ON s.product_id  = p.product_id
        LEFT JOIN core.dim_stores    st  ON s.store_id    = st.store_id
        LEFT JOIN core.dim_calendar   c  ON s.date        = c.date
        LEFT JOIN core.fact_inventory i  ON s.date = i.date
                                        AND s.store_id = i.store_id
                                        AND s.product_id = i.product_id
        GROUP BY 1,2,3,4,5,6,7,8,9,10
        ORDER BY week_start, s.store_id, s.product_id
    """
    if limit:
        query += f" LIMIT {limit}"
    return run_query(query)
