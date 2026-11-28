import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"


def get_connection(server_id):
    DATA_DIR.mkdir(exist_ok=True)

    db_path = DATA_DIR / f"server_{server_id}.db"

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def init_db(server_id):
    conn = get_connection(server_id)

    try:
        schema = (BASE_DIR / "schema.sql").read_text(encoding="utf-8")

        conn.executescript(schema)
        conn.commit()

    finally:
        conn.close()


if __name__ == "__main__":
    init_db(1)
    print("Database initialized successfully.")
