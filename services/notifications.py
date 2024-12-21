from models.database import get_db_connection
import sqlite3
from utils.logger import logger
from typing import Dict, Any


# Function to send notifications
def send_notification(alert: Dict[str, Any], current_price: float) -> None:
    """
    Send a notification about the cryptocurrency price alert.

    Args:
        alert (Dict[str, Any]): The alert details including 'cryptocurrency', 'threshold', and 'alert_type'.
        current_price (float): The current price of the cryptocurrency.

    Returns:
        None
    """
    logger.info(
        f"Alert: {alert['cryptocurrency']} price is {current_price}. Threshold: {alert['threshold']}"
    )


def save_notification(alert: Dict[str, Any], current_price: float) -> None:
    """
    Save a notification in the database if the price conditions match the alert.

    Args:
        alert (Dict[str, Any]): The alert details including 'id', 'user_id', 'name', 'threshold', 'alert_type'.
        current_price (float): The current price of the cryptocurrency.

    Returns:
        None
    """
    user_id = alert["user_id"]
    notification_text = (
        f"{alert['name'].capitalize()} is now {'above' if alert['alert_type'] == 'more' else 'below'} "
        f"{alert['threshold']} USD (current price: {current_price} USD)."
    )

    try:
        # Use context manager to handle database connection
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get the last active notification's price for this alert
            cursor.execute(
                """
                SELECT current_price FROM notifications 
                WHERE alert_id = ? AND user_id = ? AND is_read = 0 
                ORDER BY created_at DESC LIMIT 1
            """,
                (alert["id"], user_id),
            )
            last_notification = cursor.fetchone()

            # Determine if a new notification should be inserted
            if last_notification:
                last_price = last_notification[0]
                if (alert["alert_type"] == "more" and current_price <= last_price) or (
                    alert["alert_type"] == "below" and current_price >= last_price
                ):
                    return  # No need to insert a new notification

            # Insert a new notification
            query = """
            INSERT INTO notifications (alert_id, user_id, notification_text, current_price)
            VALUES (?, ?, ?, ?);
            """
            values = (alert["id"], user_id, notification_text, current_price)

            try:
                cursor.execute(query, values)
                notification_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Notification saved with ID {notification_id}")
            except sqlite3.Error as e:
                logger.error(f"Error saving notification: {e}")

    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
