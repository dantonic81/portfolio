import sqlite3
from flask import Blueprint, jsonify, session
from models.db_connection import get_db_cursor
from utils.login_required import login_required
from utils.logger import logger

notification_api = Blueprint("notification_api", __name__)


def execute_query(query, params=None):
    """
    Executes a query and returns cursor and connection.
    """
    cursor, conn = get_db_cursor()
    if cursor is None:
        return None, conn
    try:
        cursor.execute(query, params or ())
        return cursor, conn
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return None, conn


def get_notification_ownership(notification_id: int):
    """
    Returns the SQL query to check if a notification belongs to the current user.
    """
    return "SELECT user_id FROM notifications WHERE id = ?;"


@notification_api.route("/notifications", methods=["GET"])
@login_required
def get_notifications():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "User not logged in"}), 403

    query = "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC;"
    cursor, conn = execute_query(query, (user_id,))
    if cursor is None:
        return jsonify({"error": "Database connection failed"}), 500

    notifications = cursor.fetchall()
    conn.close()

    # Format notifications into a list of dictionaries for JSON response
    notifications_dict = [
        {
            "id": row[0],
            "user_id": row[1],
            "alert_id": row[2],
            "notification_text": row[4],
            "current_price": row[5],
            "is_read": bool(row[6]),
            "created_at": row[3],
        }
        for row in notifications
    ]
    return jsonify(notifications_dict)


@notification_api.route(
    "/notifications/<int:notification_id>/mark-read", methods=["POST"]
)
@login_required
def mark_notification_as_read(notification_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "User not logged in"}), 403

    check_query = get_notification_ownership(notification_id)

    cursor, conn = execute_query(check_query, (notification_id,))
    if cursor is None:
        return jsonify({"error": "Database connection failed"}), 500

    result = cursor.fetchone()
    if not result or result[0] != user_id:
        return (
            jsonify({"error": "Notification does not belong to the current user"}),
            403,
        )

    query = "UPDATE notifications SET is_read = 1 WHERE id = ?;"
    cursor.execute(query, (notification_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Notification marked as read."})


@notification_api.route("/notifications/unread-count", methods=["GET"])
@login_required
def get_unread_count():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "User not logged in"}), 403

    query = "SELECT COUNT(*) FROM notifications WHERE is_read = 0 and user_id = ?;"
    cursor, conn = execute_query(query, (user_id,))
    if cursor is None:
        return jsonify({"error": "Database connection failed"}), 500

    count = cursor.fetchone()[0]
    conn.close()

    return jsonify({"unread_count": count})
