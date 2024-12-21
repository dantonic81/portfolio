from functools import wraps
from flask import session, redirect, url_for
from typing import Callable, Any
from utils.logger import logger
from models.db_connection import get_db_cursor


def admin_required(f: Callable) -> Callable:
    """
    Decorator to restrict access to admin users.

    Args:
        f (Callable): The function to decorate.

    Returns:
        Callable: The decorated function.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs) -> Any:
        user_id = session.get("user_id")
        if not user_id or not is_admin(user_id):
            logger.warning(f"Unauthorized access attempt by user: {user_id}")
            return redirect(
                url_for("login_api.login")
            )  # Redirect to login if not an admin
        return f(*args, **kwargs)

    return decorated_function


def is_admin(user_id: int) -> bool:
    """
    Check if a user is an admin.

    Args:
        user_id (int): The ID of the user to check.

    Returns:
        bool: True if the user is an admin, otherwise False.
    """
    try:
        cursor, conn = get_db_cursor()
        if cursor is None:
            logger.error("Database cursor is None. Cannot verify admin status.")
            return False

        cursor.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

        if not user:
            logger.warning(f"User ID {user_id} not found in database.")
            return False

        return user[0] == 1
    except Exception as e:
        logger.error(f"Error checking admin status for user {user_id}: {e}")
        return False
    finally:
        if conn:
            conn.close()
