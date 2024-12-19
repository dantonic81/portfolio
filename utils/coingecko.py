from utils.logger import logger
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
import requests
from models.database import get_db_connection


# Constants
CACHE_EXPIRY = 120  # Cache expiry time in seconds
COINGECKO_API_BASE_URL = "https://api.coingecko.com/api/v3"


def fetch_data_from_api(endpoint: str, params: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch data from CoinGecko API.

    Args:
        endpoint (str): API endpoint.
        params (dict): Query parameters.

    Returns:
        Optional[List[Dict[str, Any]]]: API response as a list of dictionaries, or None on failure.
    """
    url = f"{COINGECKO_API_BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        return None


def is_cache_valid(cursor, query: str, params: Tuple) -> bool:
    """
    Check if cached data is valid.

    Args:
        cursor: SQLite cursor.
        query (str): SQL query to fetch timestamp.
        params (tuple): Query parameters.

    Returns:
        bool: True if the cache is valid, otherwise False.
    """
    cursor.execute(query, params)
    result = cursor.fetchone()
    if result and result[0]:
        last_cache_time = datetime.fromisoformat(result[0])
        return (datetime.now() - last_cache_time).total_seconds() < CACHE_EXPIRY
    return False


# Function to get current price from CoinGecko API
def get_current_price(name: str, target_currency: str = 'usd') -> Optional[float]:
    """
    Get the current price of a cryptocurrency.

    Args:
        name (str): Cryptocurrency name.
        target_currency (str): Target currency (default: 'usd').

    Returns:
        Optional[float]: Current price or None if not found.
    """
    params = {'ids': name, 'vs_currencies': target_currency}
    data = fetch_data_from_api("simple/price", params)
    if data and name in data:
        return data[name].get(target_currency)

    logger.error(f"Price data for {name} in {target_currency} not found.")
    return None


def get_top_1000_crypto() -> List[Dict[str, Any]]:
    """
    Fetch the top 1000 cryptocurrencies by market cap.

    Returns:
        List[Dict[str, Any]]: List of cryptocurrency data.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if cache exists and is valid
    cursor.execute('SELECT MAX(timestamp) FROM cryptocurrencies')
    result = cursor.fetchone()
    cached_timestamp = result[0]  # This will be in ISO 8601 format

    # Check cache validity
    if is_cache_valid(cursor, "SELECT MAX(timestamp) FROM cryptocurrencies", ()):
        logger.info("Using cached data from SQLite.")
        cursor.execute("SELECT * FROM cryptocurrencies")
        cryptos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return cryptos

    # Fetch data from API
    logger.info("Fetching data from CoinGecko API.")
    all_cryptos = []
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 250,
        'sparkline': 'false',
        'price_change_percentage': '24h',
    }

    for page in range(1, 5):
        params['page'] = page
        data = fetch_data_from_api("coins/markets", params)
        if data:
            all_cryptos.extend(data)
        else:
            logger.error(f"Error fetching data from page {page}.")
            break

    # Cache data in SQLite
    cursor.execute('DELETE FROM cryptocurrencies')  # Clear old data
    for crypto in all_cryptos:
        cursor.execute('''
            INSERT INTO cryptocurrencies (
                name, symbol, image, current_price, market_cap, market_cap_rank,
                fully_diluted_valuation, total_volume, high_24h, low_24h,
                price_change_24h, price_change_percentage_24h, market_cap_change_24h,
                market_cap_change_percentage_24h, circulating_supply, total_supply,
                max_supply, ath, ath_change_percentage, ath_date, atl,
                atl_change_percentage, atl_date, last_updated, timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            crypto.get('name'),
            crypto.get('symbol'),
            crypto.get('image'),
            crypto.get('current_price'),
            crypto.get('market_cap'),
            crypto.get('market_cap_rank'),
            crypto.get('fully_diluted_valuation'),
            crypto.get('total_volume'),
            crypto.get('high_24h'),
            crypto.get('low_24h'),
            crypto.get('price_change_24h'),
            crypto.get('price_change_percentage_24h'),
            crypto.get('market_cap_change_24h'),
            crypto.get('market_cap_change_percentage_24h'),
            crypto.get('circulating_supply'),
            crypto.get('total_supply'),
            crypto.get('max_supply'),
            crypto.get('ath'),
            crypto.get('ath_change_percentage'),
            crypto.get('ath_date'),
            crypto.get('atl'),
            crypto.get('atl_change_percentage'),
            crypto.get('atl_date'),
            crypto.get('last_updated'),
            datetime.now().isoformat()
        ))
    conn.commit()
    conn.close()

    return all_cryptos


def fetch_gainers_and_losers_owned(user_id: int, owned_coins: List[str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Fetch the top gainers and losers for owned coins with caching.

    Args:
        user_id (int): User ID.
        owned_coins (List[str]): List of owned coin IDs.

    Returns:
        Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]: Gainers and losers.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check cache validity
    if is_cache_valid(cursor, "SELECT timestamp FROM gainers_losers_cache WHERE user_id = ? AND owned_coins = ?", (user_id, ",".join(owned_coins))):
        logger.info("Using cached gainers/losers data.")
        cursor.execute("SELECT gainers, losers FROM gainers_losers_cache WHERE user_id = ? AND owned_coins = ?", (user_id, ",".join(owned_coins)))
        result = cursor.fetchone()
        conn.close()
        if result:
            return eval(result[0]), eval(result[1])

    # Fetch data from API
    logger.info("Fetching gainers and losers from API.")
    params = {"vs_currency": "usd", "ids": ",".join(owned_coins), "order": "market_cap_desc", "per_page": len(owned_coins), "price_change_percentage": "24h"}
    data = fetch_data_from_api("coins/markets", params)
    if not data:
        conn.close()
        return [], []

    # Filter and sort data
    filtered_data = [coin for coin in data if coin.get("price_change_percentage_24h") is not None]
    gainers = sorted(filtered_data, key=lambda x: x["price_change_percentage_24h"], reverse=True)
    losers = sorted(filtered_data, key=lambda x: x["price_change_percentage_24h"])

    # Cache results
    cursor.execute("DELETE FROM gainers_losers_cache WHERE user_id = ? AND owned_coins = ?",
                   (user_id, ",".join(owned_coins)))
    cursor.execute(
        "INSERT INTO gainers_losers_cache (user_id, owned_coins, gainers, losers, timestamp) VALUES (?, ?, ?, ?, ?)", (
            user_id, ",".join(owned_coins), str(gainers), str(losers), datetime.now().isoformat()
        ))
    conn.commit()
    conn.close()
    return gainers, losers