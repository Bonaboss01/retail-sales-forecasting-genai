import os
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

# ── Connection config ──────────────────────────────────────
_HOST     = "aws-1-eu-central-1.pooler.supabase.com"
_PORT     = 5432
_DATABASE = "postgres"
_USER     = "postgres.ogkdfmkybqtrsglcizzt"


def _get_password() -> str:
    raw = os.getenv("SUPABASE_DB_PASSWORD", "")
    if not raw:
        raise ValueError(
            "SUPABASE_DB_PASSWORD is not set. "
            "Run: export SUPABASE_DB_PASSWORD='your_password'"
        )
    return quote_plus(raw)


def get_engine():
    """Return a SQLAlchemy engine connected to Supabase."""
    password = _get_password()
    url = f"postgresql+psycopg2://{_USER}:{password}@{_HOST}:{_PORT}/{_DATABASE}"
    return create_engine(url, pool_pre_ping=True, pool_recycle=300)


def run_query(query: str, params: dict | None = None) -> pd.DataFrame:
    """Execute a SQL query and return the result as a DataFrame."""
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)


def run_table(table_name: str) -> pd.DataFrame:
    """Load an entire core schema table into a DataFrame."""
    return run_query(f"SELECT * FROM core.{table_name}")
