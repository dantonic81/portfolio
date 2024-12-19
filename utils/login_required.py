# utils/login_required.py
from functools import wraps
from flask import session, redirect, url_for
from utils.logger import logger
from typing import Callable


def login_required(f: Callable) -> Callable:
    """
    Decorator to enforce login requirements for a Flask route.

    Ensures that the user is logged in by checking for the presence of 'user_id'
    in the Flask session. If 'user_id' is not found, the user is redirected to
    the login page, and a warning is logged.

    Args:
        f (Callable): The Flask route function to be wrapped by the decorator.

    Returns:
        Callable: The wrapped route function.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            logger.warning("Unauthorized access attempt to %s", url_for('login_api.login'))
            return redirect(url_for('login_api.login'))  # Redirect to login if user is not logged in
        return f(*args, **kwargs)
    return decorated_function
