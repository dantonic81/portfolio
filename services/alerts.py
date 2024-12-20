from datetime import datetime
from models.database import get_db_connection
from utils.logger import logger
from typing import List, Dict, Any
from utils.coingecko import get_current_price
from services.notifications import save_notification, send_notification


def get_active_alerts() -> List[Dict[str, Any]]:
    """
    Fetch active alerts from the database and deactivate any alerts for coins no longer in the user's portfolio.

    Returns:
        List[Dict[str, Any]]: List of active alerts.
    """
    with get_db_connection() as conn:
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

    return active_alerts


def is_alert_condition_met(alert: Dict[str, Any], current_price: float) -> bool:
    """
    Check whether an alert condition is met based on the current price.

    Args:
        alert (Dict[str, Any]): The alert to check.
        current_price (float): The current price of the cryptocurrency.

    Returns:
        bool: True if the alert condition is met, otherwise False.
    """
    if alert['alert_type'] == 'more' and current_price > alert['threshold']:
        return True
    if alert['alert_type'] == 'less' and current_price < alert['threshold']:
        return True
    return False


def check_alerts() -> None:
    """
    Check all active alerts and trigger notifications if alert conditions are met.
    """
    logger.info(f"Checking alerts at {datetime.now()}")
    active_alerts = get_active_alerts()

    for alert in active_alerts:
        price_data = get_current_price(alert['name'].lower(), target_currency='usd')

        if price_data is None:
            logger.error(f"No price data available for {alert['name']}")
            continue

        current_price = price_data

        if is_alert_condition_met(alert, current_price):
            try:
                save_notification(alert, current_price)
                send_notification(alert, current_price)
                logger.info(f"Notification sent for alert {alert['id']} at price {current_price}")
            except Exception as e:
                logger.error(f"Error processing alert {alert['id']}: {e}")