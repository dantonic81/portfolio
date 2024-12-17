from flask import Blueprint, render_template, request, flash, redirect, url_for
from models.db_connection import get_db_cursor
from services.admin import admin_required

admin_api = Blueprint('admin_api', __name__)


@admin_api.route('/admin/users', methods=['GET'])
@admin_required
def view_users():
    cursor, conn = get_db_cursor()
    if cursor is None:
        return "Database connection failed.", 500

    cursor.execute("SELECT user_id, username, email, is_active FROM users")
    users = cursor.fetchall()
    conn.close()

    return render_template('admin_users.html', users=users)  # Pass the user data to a template


@admin_api.route('/admin/audit', methods=['GET'])
@admin_required
def view_audits():
    cursor, conn = get_db_cursor()
    if cursor is None:
        return "Database connection failed.", 500

    cursor.execute("SELECT * FROM audit_log")
    audits = cursor.fetchall()
    conn.close()

    return render_template('admin_audit_log.html', audits=audits)  # Pass the user data to a template


@admin_api.route('/admin/users/create', methods=['POST'])
@admin_required
def create_user():
    """Create a new user."""
    username = request.form.get('username')
    email = request.form.get('email')
    password_hash = request.form.get('password_hash')  # Assume password comes hashed already
    is_admin = request.form.get('is_admin') == 'on'  # Check if checkbox is on

    if not username or not email or not password_hash:
        flash("All fields are required to create a user.", "danger")
        return redirect(url_for('admin_api.view_users'))

    try:
        cursor, conn = get_db_cursor()
        if cursor is None:
            return "Database connection failed.", 500

        cursor.execute(
            """
            INSERT INTO users (username, email, password_hash, is_active, is_admin)
            VALUES (?, ?, ?, 1, ?)
            """,
            (username, email, password_hash, is_admin)
        )
        conn.commit()
        flash("User created successfully.", "success")
    except Exception as e:
        flash(f"Error creating user: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for('admin_api.view_users'))


@admin_api.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete a user by ID."""
    try:
        cursor, conn = get_db_cursor()
        if cursor is None:
            return "Database connection failed.", 500

        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        if cursor.rowcount == 0:
            flash("User not found.", "warning")
        else:
            conn.commit()
            flash("User deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting user: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for('admin_api.view_users'))