import sqlite3

from models.database import get_db_connection
from utils.logger import logger
from models.db_connection import get_db_cursor
from utils.coingecko import get_current_price
from services.notifications import save_notification, send_notification


def get_active_alerts():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch only active alerts
    cursor.execute("SELECT * FROM alerts WHERE status = 'active'")
    active_alerts = cursor.fetchall()

    for alert in active_alerts:
        # Check if the coin is still in the user's portfolio
        cursor.execute('SELECT * FROM portfolio WHERE user_id = ? AND name = ?', (alert['user_id'], alert['name']))
        portfolio_record = cursor.fetchone()

        if not portfolio_record:
            # Coin is no longer in the portfolio, mark the alert as inactive
            cursor.execute('UPDATE alerts SET status = ? WHERE id = ?', ('inactive', alert['id']))
            conn.commit()
            logger.warning(f"Alert for {alert['name']} is marked as inactive due to portfolio change.")

    conn.close()
    return active_alerts


# Define the job that checks alerts
def check_alerts():
    active_alerts = get_active_alerts()

    for alert in active_alerts:
        # Extract user_id from the alert
        user_id = alert['user_id']

        # Get the current price data from the CoinGecko API
        price_data = get_current_price(alert['name'].lower(), target_currency='usd')

        if price_data is not None:
            current_price = price_data

            # Check if the coin is still in the user's portfolio
            cursor, conn = get_db_cursor()
            if cursor is None:
                logger.warning(f"Error: No database connection available for user {user_id}")
                continue

            try:
                cursor.execute('SELECT * FROM portfolio WHERE user_id = ? AND name = ?', (user_id, alert['name']))
                portfolio_record = cursor.fetchone()

                if portfolio_record:
                    # Check the condition (based on the alert type)
                    if (alert['alert_type'] == 'more' and current_price > alert['threshold']) or \
                       (alert['alert_type'] == 'less' and current_price < alert['threshold']):
                        save_notification(alert, current_price)
                        # Trigger a notification
                        send_notification(alert, current_price)
                else:
                    # Coin is no longer in the portfolio, skip notification
                    logger.warning(f"Coin {alert['name']} is no longer in the portfolio for user {user_id}")


            except sqlite3.Error as e:
                logger.error(f"Error checking portfolio for user {user_id}: {e}")

            finally:
                conn.close()
        else:
            logger.info(f"Error: No price data available for {alert['name']}")