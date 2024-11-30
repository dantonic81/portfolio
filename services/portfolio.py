from models.database import get_db_connection
import sqlite3


# Fetch portfolio from SQLite
def read_portfolio():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, abbreviation, amount FROM portfolio')
    portfolio = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return portfolio


def calculate_portfolio_value(portfolio, top_1000):
    # Build a lookup dictionary for fast access by both name and symbol
    price_lookup = {
        crypto['name'].lower(): {'price': crypto['current_price'], 'rank': crypto['market_cap_rank'], 'image': crypto['image']}
        for crypto in top_1000
    }

    # Add symbol-based lookup as a fallback
    price_lookup.update({
        crypto['symbol'].upper(): {'price': crypto['current_price'], 'rank': crypto['market_cap_rank'], 'image': crypto['image']}
        for crypto in top_1000
    })

    total_value = 0.0
    for asset in portfolio:
        name = asset['name'].lower()
        symbol = asset['abbreviation']
        amount = asset['amount']

        # Try to look up by name first, then fallback to symbol
        crypto_data = price_lookup.get(name) or price_lookup.get(symbol, {'price': 0, 'rank': None, 'image': None})

        current_price = crypto_data['price']
        asset_value = amount * current_price

        asset['current_price'] = current_price
        asset['value'] = round(asset_value, 2)
        asset['rank'] = crypto_data['rank']
        asset['image'] = crypto_data['image']

        total_value += asset_value

    return round(total_value, 2)


def fetch_owned_coins_from_db(db_path="crypto_portfolio.db"):
    """
    Fetch the abbreviations of the coins in the portfolio from the database.

    Args:
        db_path (str): The path to the SQLite database.

    Returns:
        list: List of coin abbreviations owned (e.g., ["bitcoin", "ethereum"]).
    """
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    # Fetch all owned coin abbreviations
    cursor.execute("SELECT abbreviation FROM portfolio")
    owned_coins = [row[0].lower() for row in cursor.fetchall()]

    connection.close()
    return owned_coins


def get_assets_by_query(query):
    with sqlite3.connect('crypto_portfolio.db') as conn:
        cursor = conn.cursor()

        # Use parameterized queries to prevent SQL injection
        cursor.execute("SELECT id, name, amount FROM portfolio WHERE name LIKE ?", ('%' + query + '%',))
        assets = cursor.fetchall()

    # Return the results in a structured format (list of dictionaries)
    return [{'id': asset[0], 'asset_name': asset[1], 'amount': asset[2]} for asset in assets]
