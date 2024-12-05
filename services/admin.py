from functools import wraps
from flask import session, redirect, url_for
import os

from werkzeug.security import generate_password_hash

from models.db_connection import get_db_cursor


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not is_admin(session['user_id']):
            return redirect(url_for('api.login'))  # Redirect to login if not an admin
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


def create_default_admin():
    username = os.getenv('ADMIN_USERNAME')
    email = os.getenv('ADMIN_EMAIL')
    password = os.getenv('ADMIN_PASSWORD')
    password_hash = generate_password_hash(password)

    cursor, conn = get_db_cursor()
    try:
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, is_admin, is_active)
            VALUES (?, ?, ?, 1, 1)
            ON CONFLICT (email) DO NOTHING
        ''', (username, email, password_hash))
        conn.commit()
        print(f"Default admin account ensured: {username} ({email})")
    except Exception as e:
        print(f"Error ensuring default admin account: {e}")
    finally:
        conn.close()

