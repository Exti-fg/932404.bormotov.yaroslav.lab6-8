import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

DB_PATH = Path(__file__).with_name("orders.sqlite")


@contextmanager
def connect():
    with closing(sqlite3.connect(DB_PATH)) as db, db:
        db.row_factory = sqlite3.Row
        yield db


def initialize():
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                customer_name TEXT NOT NULL CHECK (length(trim(customer_name)) > 0),
                total_amount REAL NOT NULL CHECK (total_amount >= 0),
                status TEXT NOT NULL DEFAULT 'new'
                    CHECK (status IN ('new', 'paid', 'shipped', 'delivered'))
            )
        """)


def list_orders(status: str | None):
    with connect() as db:
        if status is None:
            rows = db.execute("SELECT * FROM orders ORDER BY id")
        else:
            rows = db.execute("SELECT * FROM orders WHERE status = ? ORDER BY id", (status,))
        return [dict(row) for row in rows]


def create_order(name: str, amount: float, status: str):
    with connect() as db:
        cursor = db.execute(
            "INSERT INTO orders (customer_name, total_amount, status) VALUES (?, ?, ?)",
            (name, amount, status),
        )
        return dict(db.execute("SELECT * FROM orders WHERE id = ?", (cursor.lastrowid,)).fetchone())


def change_status(order_id: int, status: str):
    with connect() as db:
        cursor = db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        if cursor.rowcount:
            return dict(db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone())
        return None


def delete_order(order_id: int) -> bool:
    with connect() as db:
        return db.execute("DELETE FROM orders WHERE id = ?", (order_id,)).rowcount > 0
