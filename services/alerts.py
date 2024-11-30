from models.database import get_db_connection
from datetime import datetime
from utils.coingecko import get_current_price
from services.notifications import save_notification, send_notification


def get_active_alerts():
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM alerts WHERE status = 'active'"  # Only fetch active alerts
    cursor.execute(query)

    alerts = cursor.fetchall()
    conn.close()

    return alerts


# Define the job that checks alerts
def check_alerts():
    print("Checking alerts at", datetime.now())
    active_alerts = get_active_alerts()

    for alert in active_alerts:
        # Get the current price data from the CoinGecko API
        price_data = get_current_price(alert['name'].lower(), target_currency='usd')

        if price_data is not None:
            current_price = price_data

            # Check the condition (based on the alert type)
            if (alert['alert_type'] == 'more' and current_price > alert['threshold']) or \
               (alert['alert_type'] == 'less' and current_price < alert['threshold']):
                save_notification(alert, current_price)
                # Trigger a notification
                send_notification(alert, current_price)
        else:
            print(f"Error: No price data available for {alert['name']}")
