from models.database import get_db_connection
import sqlite3


# Fetch portfolio from SQLite
def read_portfolio(user_id):
    """
    Retrieve the user's portfolio from the SQLite database.

    Args:
        user_id (int): The ID of the user whose portfolio is to be fetched.

    Returns:
        list: A list of dictionaries representing the portfolio (each dictionary includes id, user_id, name, abbreviation, and amount).
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_id, name, abbreviation, amount FROM portfolio WHERE user_id = ?",
            (user_id,),
        )
        portfolio = [dict(row) for row in cursor.fetchall()]
    return portfolio


def calculate_portfolio_value(portfolio, top_1000):
    """
    Calculate the total value of a user's portfolio based on current crypto prices.

    Args:
        portfolio (list): The user's portfolio (list of assets).
        top_1000 (list): A list of the top 1000 cryptocurrencies.

    Returns:
        float: The total value of the portfolio.
    """
    # Build a lookup dictionary for fast access by both name and symbol
    price_lookup = {
        crypto["name"].lower(): {
            "price": crypto["current_price"],
            "rank": crypto["market_cap_rank"],
            "image": crypto["image"],
        }
        for crypto in top_1000
    }
    price_lookup.update(
        {
            crypto["symbol"].upper(): {
                "price": crypto["current_price"],
                "rank": crypto["market_cap_rank"],
                "image": crypto["image"],
            }
            for crypto in top_1000
        }
    )

    total_value = 0.0
    for asset in portfolio:
        name = asset["name"].lower()
        symbol = asset["abbreviation"]
        amount = asset["amount"]

        # Try to look up by name first, then fallback to symbol
        crypto_data = price_lookup.get(name) or price_lookup.get(
            symbol, {"price": 0, "rank": None, "image": None}
        )

        current_price = crypto_data["price"]
        asset_value = amount * current_price

        asset.update(
            {
                "current_price": current_price,
                "value": round(asset_value, 2),
                "rank": crypto_data["rank"],
                "image": crypto_data["image"],
            }
        )

        total_value += asset_value

    return round(total_value, 2)


def fetch_owned_coins_from_db(user_id, db_path="crypto_portfolio.db"):
    """
    Fetch the abbreviations of the coins in the portfolio from the database based on user_id.

    Args:
        db_path (str): The path to the SQLite database.
        user_id (int): The ID of the user.

    Returns:
        list: List of coin abbreviations owned (e.g., ["bitcoin", "ethereum"]).
    """
    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT name FROM portfolio WHERE user_id = ?", (user_id,)
        )
        owned_coins = [row[0].lower() for row in cursor.fetchall()]
    return owned_coins


def get_assets_by_query(query, user_id):
    """
    Search for assets in the portfolio based on a query.

    Args:
        query (str): The search query (can be part of the asset name).
        user_id (int): The ID of the user.

    Returns:
        list: A list of assets matching the query (each asset is represented as a dictionary).
    """
    with sqlite3.connect("crypto_portfolio.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_id, name, amount FROM portfolio WHERE name LIKE ? AND user_id = ?",
            ("%" + query + "%", user_id),
        )
        assets = cursor.fetchall()

    # Return the results in a structured format (list of dictionaries)
    return [
        {"id": asset[0], "asset_name": asset[2], "amount": asset[3]} for asset in assets
    ]
