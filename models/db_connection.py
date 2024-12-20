import sqlite3
from typing import Optional, Tuple
from utils.logger import logger


DATABASE = 'crypto_portfolio.db'


def get_db_connection() -> sqlite3.Connection:
    """
    Establish and configure a database connection.

    Returns:
        sqlite3.Connection: Configured SQLite database connection.
    """
    try:
        conn = sqlite3.connect(DATABASE)
        conn.execute("PRAGMA foreign_keys = ON;")  # Enforce foreign key constraints
        conn.execute("PRAGMA journal_mode = WAL;")  # Enable Write-Ahead Logging for better concurrency
        conn.row_factory = sqlite3.Row  # Return rows as dictionary-like objects
        return conn
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to establish database connection: {e}")


def get_db_cursor() -> Tuple[Optional[sqlite3.Cursor], Optional[sqlite3.Connection]]:
    """
    Create and return a database cursor along with the connection.

    Returns:
        Tuple[Optional[sqlite3.Cursor], Optional[sqlite3.Connection]]: Database cursor and connection, or (None, None) on failure.
    """
    try:
        conn = get_db_connection()
        if conn is None:
            return None, None

        cursor = conn.cursor()
        return cursor, conn
    except sqlite3.Error as e:
        logger.error(f"Error obtaining database cursor: {e}")
        return None, None