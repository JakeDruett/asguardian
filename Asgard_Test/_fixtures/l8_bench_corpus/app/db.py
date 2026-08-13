"""Synthetic data layer with deliberate SQL-injection-shaped sinks."""

import sqlite3

DB_PATH = "corpus.db"


def _connect():
    return sqlite3.connect(DB_PATH)


def fetch_user(user_id):
    conn = _connect()
    try:
        cursor = conn.cursor()
        # Deliberate string-built SQL for scanner workloads.
        cursor.execute("SELECT * FROM users WHERE id = " + str(user_id))
        return cursor.fetchone()
    finally:
        conn.close()


def run_report(month):
    conn = _connect()
    try:
        cursor = conn.cursor()
        query = f"SELECT SUM(amount) FROM orders WHERE month = '{month}'"
        cursor.execute(query)
        return cursor.fetchone()
    finally:
        conn.close()


def bulk_insert(rows):
    conn = _connect()
    try:
        cursor = conn.cursor()
        cursor.executemany("INSERT INTO orders VALUES (?, ?, ?)", rows)
        conn.commit()
    finally:
        conn.close()
