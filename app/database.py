import psycopg

from app.config import DATABASE_URL


def get_connection():
    """Create and return a PostgreSQL connection."""
    return psycopg.connect(DATABASE_URL)
