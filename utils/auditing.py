from models.db_connection import get_db_cursor
from utils.logger import logger
import sqlite3
import time
from flask import request


def log_audit_event(request, event_type: str, username: str, status: str, error_message: str = None) -> None:
    """Logs an audit event to the SQLite database with retry logic.

    Args:
        request (flask.Request): The Flask request object.
        event_type (str): The type of the event being logged.
        username (str): The username associated with the event.
        status (str): The status of the event (e.g., "success", "failure").
        error_message (str, optional): An optional error message for failed events.
    """
    ip_address = get_client_ip()
    user_agent = request.headers.get("User-Agent", "Unknown")  # Default to "Unknown" if missing
    retries = 5
    initial_wait_time = 0.1  # Starting backoff time (in seconds)
    max_wait_time = 2.0  # Cap the backoff time

    while retries > 0:
        try:
            # Get the connection and cursor
            cursor, conn = get_db_cursor()
            try:
                cursor.execute('''
                    INSERT INTO audit_log (event_type, username, ip_address, user_agent, status, error_message)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (event_type, username, ip_address, user_agent, status, error_message))
                conn.commit()
                logger.info(f"Audit event logged successfully: event_type={event_type}, username={username}")
                return  # Exit after successful logging
            finally:
                # Ensure cursor and connection are closed
                cursor.close()
                conn.close()

        except sqlite3.OperationalError as e:
            # Retry only on database lock
            if "database is locked" in str(e):
                retries -= 1
                wait_time = min(initial_wait_time * (2 ** (5 - retries)), max_wait_time)  # Exponential backoff
                logger.warning(
                    f"Database is locked. Retrying in {wait_time:.2f} seconds... "
                    f"({retries} retries left) - event_type={event_type}, username={username}"
                )
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to log audit event: {str(e)} - event_type={event_type}, username={username}")
                raise

        except Exception as e:
            logger.error(f"Unexpected error during audit logging: {str(e)} - event_type={event_type}, username={username}")
            raise

    # If retries exhausted
    logger.error(f"Max retries reached. Could not log audit event: event_type={event_type}, username={username}")


def get_client_ip() -> str:
    """Retrieve the client's IP address from the request.

    Returns:
        str: The client's IP address.
    """
    x_forwarded_for = request.headers.get('X-Forwarded-For')
    if x_forwarded_for:
        # Extract the first IP in the list
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        # Fallback to remote_addr if no X-Forwarded-For is present
        ip = request.remote_addr or "Unknown"  # Default to "Unknown" if missing
    return ip
