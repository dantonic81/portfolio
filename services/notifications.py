from models.database import get_db_connection
import sqlite3
from utils.logger import logger


# Function to send notifications
def send_notification(alert, current_price):
    logger.info(f"Alert: {alert['cryptocurrency']} price is {current_price}. Threshold: {alert['threshold']}")


def save_notification(alert, current_price):
    notification_text = (
        f"{alert['name']} is now {'above' if alert['alert_type'] == 'more' else 'below'} "
        f"{alert['threshold']} USD (current price: {current_price} USD)."
    )

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get the last active notification's price for this alert
    cursor.execute('''
        SELECT current_price FROM notifications 
        WHERE alert_id = ? AND is_read = 0 
        ORDER BY created_at DESC LIMIT 1
    ''', (alert['id'],))
    last_notification = cursor.fetchone()

    # If there is a previous notification and the price hasn't changed as required, do not insert a new notification
    if last_notification:
        last_price = last_notification[0]

        if alert['alert_type'] == 'more' and current_price <= last_price:
            # If the alert type is 'more' and the current price is not higher than the last price, don't insert
            conn.close()
            return

        if alert['alert_type'] == 'below' and current_price >= last_price:
            # If the alert type is 'below' and the current price is not lower than the last price, don't insert
            conn.close()
            return

    # If conditions are met, insert a new notification
    query = """
    INSERT INTO notifications (alert_id, notification_text, current_price)
    VALUES (?, ?, ?);
    """
    values = (alert['id'], notification_text, current_price)

    try:
        cursor.execute(query, values)
        notification_id = cursor.lastrowid
        conn.commit()
        print(f"Notification saved with ID {notification_id}")
    except sqlite3.Error as e:
        print(f"Error saving notification: {e}")
    finally:
        conn.close()