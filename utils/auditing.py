from models.db_connection import get_db_cursor
from utils.logger import logger
import sqlite3
import time


def log_audit_event(request, event_type, username, status, error_message=None):
    """Logs an audit event to the SQLite database with retry logic."""
    ip_address = request.remote_addr
    user_agent = request.headers.get("User-Agent")

    retries = 5
    initial_wait_time = 0.1  # Starting backoff time (in seconds)

    while retries > 0:
        cursor, conn = get_db_cursor()
        if cursor is None:
            print("Failed to log audit event: Database connection failed.")
            return

        try:
            # Attempt the database operation
            cursor.execute('''
                INSERT INTO audit_log (event_type, username, ip_address, user_agent, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (event_type, username, ip_address, user_agent, status, error_message))
            conn.commit()
            print(f"Audit event logged successfully.")
            return  # Exit the function after a successful operation
        except sqlite3.OperationalError as e:
            # Check if the error is due to a database lock
            if "database is locked" in str(e):
                retries -= 1
                wait_time = initial_wait_time * (2 ** (5 - retries))  # Exponential backoff
                logger.warning(f"Database is locked. Retrying in {wait_time:.2f} seconds... ({retries} retries left)")
                time.sleep(wait_time)  # Wait before retrying
            else:
                # If it's not a lock error, raise the exception
                logger.error(f"Failed to log audit event: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise
        finally:
            conn.close()

    # If all retries are exhausted, log an error
    logger.error("Max retries reached. Could not log audit event due to database lock.")