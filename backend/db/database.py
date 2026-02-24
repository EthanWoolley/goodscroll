import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "scroll.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    schema = SCHEMA_PATH.read_text()
    conn = get_connection()
    conn.executescript(schema)
    conn.close()
