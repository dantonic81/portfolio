import sqlite3

DATABASE = 'crypto_portfolio.db'


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def get_db_cursor():
    """Returns a database cursor and connection."""
    conn = get_db_connection()
    return conn.cursor(), conn