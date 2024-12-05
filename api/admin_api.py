from flask import Blueprint, render_template
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
