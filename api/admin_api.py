from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash
from utils.logger import logger
from models.db_connection import get_db_cursor
from services.admin import admin_required

admin_api = Blueprint('admin_api', __name__)


def handle_db_query(query, params=None):
    """Helper function to manage database connections and queries."""
    try:
        cursor, conn = get_db_cursor()
        if cursor is None:
            return None, "Database connection failed.", 500

        cursor.execute(query, params or ())
        result = cursor.fetchall()
        conn.commit()
        return result, None
    except Exception as e:
        logger.error(f"Database error: {e}")
        return None, f"Database error: {e}", 500
    finally:
        if conn:
            conn.close()


@admin_api.route('/admin/users', methods=['GET'])
@admin_required
def view_users():
    query = "SELECT user_id, username, email, is_active, is_admin FROM users WHERE NOT is_deleted"
    users, error = handle_db_query(query)

    if error:
        # Handle query failure
        flash("Error retrieving user data. Please try again later.", "danger")
        return render_template('admin_users.html', users=[])

    if not users:
        # Handle case where no users exist
        flash("No users found. You can add new users below.", "info")

    # Render the page regardless, passing the users list
    return render_template('admin_users.html', users=users)


@admin_api.route('/admin/audit', methods=['GET'])
@admin_required
def view_audits():
    query = "SELECT * FROM audit_log ORDER BY created_at DESC"
    audits, error = handle_db_query(query)

    if error:
        # Handle database query failure
        flash("Error retrieving audit logs. Please try again later.", "danger")
        return render_template('admin_audit_log.html', audits=[])
    if not audits:
        # Handle case where there are no audit logs
        flash("No audit logs available.", "info")

    # Render the audit log template, passing the results (even if empty)
    return render_template('admin_audit_log.html', audits=audits)


@admin_api.route('/admin/users/create', methods=['POST'])
@admin_required
def create_user():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    is_admin = request.form.get('is_admin') == 'on'

    if not username or not email or not password:
        flash("All fields are required to create a user.", "danger")
        return redirect(url_for('admin_api.view_users'))

    try:
        hashed_password = generate_password_hash(password)

        query = """
            INSERT INTO users (username, email, password_hash, is_active, is_admin)
            VALUES (?, ?, ?, 1, ?)
        """
        params = (username, email, hashed_password, is_admin)
        _, error = handle_db_query(query, params)

        if error:
            flash(error, "danger")
        else:
            flash("User created successfully.", "success")
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        flash("An unexpected error occurred while creating the user.", "danger")

    return redirect(url_for('admin_api.view_users'))


@admin_api.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    try:
        # Check remaining admins
        query_check = """
            SELECT COUNT(*) FROM users 
            WHERE is_deleted = 0 AND is_admin = 1 AND user_id != ?
        """
        remaining_admins, error = handle_db_query(query_check, (user_id,))
        if error:
            flash(error, "danger")
            return redirect(url_for('admin_api.view_users'))

        if remaining_admins[0][0] <= 0:
            flash('Cannot delete the only admin user.', 'danger')
        else:
            query_delete = "UPDATE users SET is_deleted = 1 WHERE user_id = ?"
            _, error = handle_db_query(query_delete, (user_id,))
            if error:
                flash(error, "danger")
            else:
                flash('User marked as deleted.', 'success')
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        flash("An unexpected error occurred while deleting the user.", "danger")

    return redirect(url_for('admin_api.view_users'))
