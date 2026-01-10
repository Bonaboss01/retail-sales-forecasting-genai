from __future__ import annotations

import numpy as np
import pandas as pd


def fit_elasticity_loglog(g: pd.DataFrame) -> float:
    """
    log(units_sold) = a + b*log(price) + controls...
    Returns b (price elasticity, negative usually).
    """
    g = g[(g["units_sold"] > 0) & (g["price"] > 0)].copy()
    if len(g) < 200:
        return np.nan

    g["log_units"] = np.log(g["units_sold"].astype(float))
    g["log_price"] = np.log(g["price"].astype(float))
    g["discount_rate"] = (g.get("discount_pct", 0) / 100.0).astype(float)

    # controls
    is_weekend = g.get("is_weekend", 0).astype(int).values
    is_holiday = g.get("is_holiday", 0).astype(int).values
    is_payday = g.get("is_payday", 0).astype(int).values

    X = np.column_stack([
        np.ones(len(g)),
        g["log_price"].values,
        g["discount_rate"].values,
        is_weekend,
        is_holiday,
        is_payday,
    ])
    y = g["log_units"].values

    b = np.linalg.lstsq(X, y, rcond=None)[0]
    return float(b[1])


def elasticity_by_category(df: pd.DataFrame) -> pd.DataFrame:
    required = {"category", "units_sold", "price"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Missing columns in df: {missing}")

    out = (
        df.groupby("category", dropna=False)
          .apply(fit_elasticity_loglog)
          .reset_index(name="price_elasticity")
          .sort_values("price_elasticity")
    )
    return out


def save_elasticity_csv(df: pd.DataFrame, out_path: str) -> pd.DataFrame:
    el = elasticity_by_category(df)
    el.to_csv(out_path, index=False)
    return el