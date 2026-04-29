"""
manage_policies.py
------------------
Standalone script for managing SunnyBest policy regimes in Supabase.
Run this manually when a business decision changes a policy.
Has NO connection to the daily data generation pipeline.

Usage examples:
    python manage_policies.py list
    python manage_policies.py add
    python manage_policies.py deactivate "Telecom Seasonal Push"
    python manage_policies.py extend "Mall Expansion Drive" 2026-12-31
"""

import sys
import pandas as pd
from datetime import date
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus


# =========================================================
# CONNECTION
# =========================================================

password = quote_plus("YOUR_OWNER_PASSWORD")

SUPABASE_DB_URL = (
    f"postgresql+psycopg2://postgres:{password}"
    "@db.ogkdfmkybqtrsglcizzt.supabase.co:5432/postgres?sslmode=require"
)

engine = create_engine(SUPABASE_DB_URL, pool_pre_ping=True)

TABLE = "core.dim_policy_regimes"


# =========================================================
# READ
# =========================================================

def list_policies():
    """Print all policies currently in Supabase."""
    df = pd.read_sql(f"SELECT * FROM {TABLE} ORDER BY start_date ASC", engine)

    if df.empty:
        print("No policies found in Supabase.")
        return

    today = pd.Timestamp(date.today())
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"]   = pd.to_datetime(df["end_date"])
    df["status"]     = df["end_date"].apply(
        lambda e: "ACTIVE" if e >= today else "EXPIRED"
    )

    print(f"\n{'ID':<5} {'Policy Name':<45} {'Category':<25} {'Store Type':<15} "
          f"{'Start':<12} {'End':<12} {'Demand':>8} {'Status'}")
    print("-" * 140)
    for _, r in df.iterrows():
        print(
            f"{r.get('policy_id', '-'):<5} "
            f"{str(r['policy_name']):<45} "
            f"{str(r.get('affected_category') or 'All'):<25} "
            f"{str(r.get('affected_store_type') or 'All'):<15} "
            f"{str(r['start_date'].date()):<12} "
            f"{str(r['end_date'].date()):<12} "
            f"{r.get('demand_multiplier', 1.0):>8.2f} "
            f"{r['status']}"
        )
    print()


# =========================================================
# ADD
# =========================================================

def add_policy(
    policy_name: str,
    start_date: str,
    end_date: str,
    demand_multiplier: float        = 1.0,
    discount_cap_pct: int           = 30,
    replenishment_multiplier: float = 1.0,
    service_intensity_multiplier: float = 1.0,
    affected_category: str | None   = None,
    affected_store_type: str | None = None,
):
    """
    Add a new policy regime to Supabase.

    Parameters
    ----------
    policy_name                  : unique name for the policy
    start_date / end_date        : "YYYY-MM-DD"
    demand_multiplier            : e.g. 1.15 = +15% demand
    discount_cap_pct             : max discount allowed under this policy
    replenishment_multiplier     : e.g. 1.10 = order 10% more stock
    service_intensity_multiplier : affects store operations staffing
    affected_category            : None means all categories
    affected_store_type          : None means all store types
    """
    # Check for duplicate name
    existing = pd.read_sql(
        f"SELECT policy_name FROM {TABLE} WHERE policy_name = :name",
        engine,
        params={"name": policy_name},
    )
    if not existing.empty:
        print(f"Policy '{policy_name}' already exists. Use update or choose a different name.")
        return

    new_row = pd.DataFrame([{
        "policy_name":                   policy_name,
        "start_date":                    pd.to_datetime(start_date),
        "end_date":                      pd.to_datetime(end_date),
        "affected_category":             affected_category,
        "affected_store_type":           affected_store_type,
        "demand_multiplier":             demand_multiplier,
        "discount_cap_pct":              discount_cap_pct,
        "replenishment_multiplier":      replenishment_multiplier,
        "service_intensity_multiplier":  service_intensity_multiplier,
    }])

    new_row.to_sql(
        name="dim_policy_regimes",
        con=engine,
        schema="core",
        if_exists="append",
        index=False,
        method="multi",
    )

    print(f"Added policy: '{policy_name}'  ({start_date} -> {end_date})")


# =========================================================
# DEACTIVATE
# =========================================================

def deactivate_policy(policy_name: str):
    """
    End a policy immediately by setting its end_date to today.
    Does not delete the row — keeps history intact.
    """
    today = date.today().isoformat()

    with engine.begin() as conn:
        result = conn.execute(
            text(f"""
                UPDATE {TABLE}
                SET end_date = :today
                WHERE policy_name = :name
                  AND end_date >= :today
            """),
            {"today": today, "name": policy_name},
        )

    if result.rowcount == 0:
        print(f"No active policy found with name '{policy_name}'.")
    else:
        print(f"Deactivated '{policy_name}' — end_date set to {today}.")


# =========================================================
# EXTEND
# =========================================================

def extend_policy(policy_name: str, new_end_date: str):
    """Push the end_date of an existing policy forward."""
    with engine.begin() as conn:
        result = conn.execute(
            text(f"""
                UPDATE {TABLE}
                SET end_date = :new_end
                WHERE policy_name = :name
            """),
            {"new_end": new_end_date, "name": policy_name},
        )

    if result.rowcount == 0:
        print(f"No policy found with name '{policy_name}'.")
    else:
        print(f"Extended '{policy_name}' -> new end date: {new_end_date}.")


# =========================================================
# UPDATE MULTIPLIERS
# =========================================================

def update_multiplier(
    policy_name: str,
    demand: float | None             = None,
    replenishment: float | None      = None,
    service_intensity: float | None  = None,
    discount_cap: int | None         = None,
):
    """
    Update one or more multipliers on an existing policy.
    Only the fields you pass will be changed.
    """
    updates = []
    params  = {"name": policy_name}

    if demand is not None:
        updates.append("demand_multiplier = :demand")
        params["demand"] = demand
    if replenishment is not None:
        updates.append("replenishment_multiplier = :replenishment")
        params["replenishment"] = replenishment
    if service_intensity is not None:
        updates.append("service_intensity_multiplier = :service_intensity")
        params["service_intensity"] = service_intensity
    if discount_cap is not None:
        updates.append("discount_cap_pct = :discount_cap")
        params["discount_cap"] = discount_cap

    if not updates:
        print("Nothing to update — pass at least one multiplier argument.")
        return

    sql = f"UPDATE {TABLE} SET {', '.join(updates)} WHERE policy_name = :name"

    with engine.begin() as conn:
        result = conn.execute(text(sql), params)

    if result.rowcount == 0:
        print(f"No policy found with name '{policy_name}'.")
    else:
        print(f"Updated '{policy_name}': {', '.join(updates)}")


# =========================================================
# CLI
# =========================================================

def print_usage():
    print("""
Usage:
  python manage_policies.py list
  python manage_policies.py deactivate "<policy_name>"
  python manage_policies.py extend "<policy_name>" <YYYY-MM-DD>
  python manage_policies.py add
      (runs interactive prompt)
""")


def interactive_add():
    print("\n--- Add New Policy ---")
    name       = input("Policy name          : ").strip()
    start      = input("Start date (YYYY-MM-DD): ").strip()
    end        = input("End date   (YYYY-MM-DD): ").strip()
    category   = input("Affected category (Enter to skip): ").strip() or None
    store_type = input("Affected store type (Enter to skip): ").strip() or None
    demand     = float(input("Demand multiplier (default 1.0): ").strip() or 1.0)
    replen     = float(input("Replenishment multiplier (default 1.0): ").strip() or 1.0)
    service    = float(input("Service intensity multiplier (default 1.0): ").strip() or 1.0)
    discount   = int(input("Discount cap % (default 30): ").strip() or 30)

    add_policy(
        policy_name=name,
        start_date=start,
        end_date=end,
        demand_multiplier=demand,
        discount_cap_pct=discount,
        replenishment_multiplier=replen,
        service_intensity_multiplier=service,
        affected_category=category,
        affected_store_type=store_type,
    )


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or args[0] == "list":
        list_policies()

    elif args[0] == "add":
        interactive_add()

    elif args[0] == "deactivate":
        if len(args) < 2:
            print("Usage: python manage_policies.py deactivate \"<policy_name>\"")
        else:
            deactivate_policy(args[1])

    elif args[0] == "extend":
        if len(args) < 3:
            print("Usage: python manage_policies.py extend \"<policy_name>\" <YYYY-MM-DD>")
        else:
            extend_policy(args[1], args[2])

    else:
        print_usage()
