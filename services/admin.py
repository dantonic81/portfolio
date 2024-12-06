from functools import wraps
from flask import session, redirect, url_for


from models.db_connection import get_db_cursor


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not is_admin(session['user_id']):
            return redirect(url_for('login_api.login'))  # Redirect to login if not an admin
        return f(*args, **kwargs)
    return decorated_function


def is_admin(user_id):
    cursor, conn = get_db_cursor()
    if cursor is None:
        return False
    cursor.execute('SELECT is_admin FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user and user[0] == 1
