import sqlite3

from flask import Blueprint, jsonify, session
from models.db_connection import get_db_cursor
from utils.login_required import login_required


notification_api = Blueprint('notification_api', __name__)


@notification_api.route('/notifications', methods=['GET'])
@login_required
def get_notifications():
    user_id = session.get('user_id')  # Get the logged-in user's user_id
    if not user_id:
        return jsonify({'error': 'User not logged in'}), 403

    query = "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC;"
    cursor, conn = get_db_cursor()
    if cursor is None:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor.execute(query, (user_id,))
    notifications = cursor.fetchall()
    conn.close()
    # Format notifications into a list of dictionaries for JSON response
    notifications_dict = [
        {
            "id": row[0],
            "user_id": row[1],
            "alert_id": row[2],
            "notification_text": row[4],  # This should be the actual notification message
            "current_price": row[5],       # This should be the price value
            "is_read": bool(row[6]),       # Ensure this is a boolean
            "created_at": row[3]          # Timestamp field
        }
        for row in notifications
    ]
    return jsonify(notifications_dict)


@notification_api.route('/notifications/<int:notification_id>/mark-read', methods=['POST'])
@login_required
def mark_notification_as_read(notification_id):
    user_id = session.get('user_id')  # Get the logged-in user's user_id
    if not user_id:
        return jsonify({'error': 'User not logged in'}), 403

    # Check if the notification belongs to the current user
    check_query = "SELECT user_id FROM notifications WHERE id = ?;"
    cursor, conn = get_db_cursor()
    if cursor is None:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor.execute(check_query, (notification_id,))
    result = cursor.fetchone()

    if not result or result[0] != user_id:
        conn.close()
        return jsonify({'error': 'Notification does not belong to the current user'}), 403


    query = "UPDATE notifications SET is_read = 1 WHERE id = ?;"  # SQLite uses ? as a placeholder
    cursor, conn = get_db_cursor()
    if cursor is None:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor.execute(query, (notification_id,))
        conn.commit()
        return jsonify({"message": "Notification marked as read."})
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@notification_api.route('/notifications/unread-count', methods=['GET'])
@login_required
def get_unread_count():
    user_id = session.get('user_id')  # Get the logged-in user's user_id
    if not user_id:
        return jsonify({'error': 'User not logged in'}), 403

    query = "SELECT COUNT(*) FROM notifications WHERE is_read = 0 and user_id = ?;"
    cursor, conn = get_db_cursor()
    if cursor is None:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor.execute(query, (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return jsonify({"unread_count": count})