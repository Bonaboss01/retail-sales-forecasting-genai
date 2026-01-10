from __future__ import annotations

import os
import pandas as pd

from src.pricing.elasticity import save_elasticity_csv


def main():
    # use your merged data file if you already saved one
    # If not, point this to your actual merged file path you use in notebooks.
    merged_path = os.getenv("MERGED_DATA_PATH", "data/processed/sunnybest_merged_df.csv")
    out_path = os.getenv("ELASTICITY_OUT_PATH", "data/processed/elasticity_by_category.csv")

    df = pd.read_csv(merged_path, parse_dates=["date"])

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    save_elasticity_csv(df, out_path)

    print(f"✅ Saved elasticity artifact to: {out_path}")


if __name__ == "__main__":
    main()