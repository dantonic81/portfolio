from utils.logger import logger
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
import requests
from models.database import get_db_connection
from pydantic import BaseModel, ValidationError
import json


# Constants
CACHE_EXPIRY = 120  # Cache expiry time in seconds
COINGECKO_API_BASE_URL = "https://api.coingecko.com/api/v3"

# SQL Query Constants
SELECT_CACHE_QUERY = """
    SELECT gainers, losers FROM gainers_losers_cache 
    WHERE user_id = ? AND owned_coins = ?
"""
DELETE_CACHE_QUERY = """
    DELETE FROM gainers_losers_cache 
    WHERE user_id = ? AND owned_coins = ?
"""
INSERT_CACHE_QUERY = """
    INSERT INTO gainers_losers_cache (user_id, owned_coins, gainers, losers, timestamp) 
    VALUES (?, ?, ?, ?, ?)
"""


class CryptoData(BaseModel):
    name: str
    symbol: str
    image: Optional[str]
    current_price: Optional[float]
    market_cap: Optional[int]
    market_cap_rank: Optional[int]
    fully_diluted_valuation: Optional[int]
    total_volume: Optional[float]
    high_24h: Optional[float]
    low_24h: Optional[float]
    price_change_24h: Optional[float]
    price_change_percentage_24h: Optional[float]
    market_cap_change_24h: Optional[float]
    market_cap_change_percentage_24h: Optional[float]
    circulating_supply: Optional[float]
    total_supply: Optional[float]
    max_supply: Optional[float]
    ath: Optional[float]
    ath_change_percentage: Optional[float]
    ath_date: Optional[str]
    atl: Optional[float]
    atl_change_percentage: Optional[float]
    atl_date: Optional[str]
    last_updated: Optional[str]


def fetch_data_from_api(
    endpoint: str, params: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
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
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        return None


def validate_crypto_data(data: List[Dict[str, Any]]) -> List[CryptoData]:
    valid_data = []
    for item in data:
        try:
            valid_data.append(CryptoData(**item))
        except ValidationError as e:
            logger.warning(f"Validation failed for item: {e}")
    return valid_data


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
def get_current_price(name: str, target_currency: str = "usd") -> Optional[float]:
    """
    Get the current price of a cryptocurrency.

    Args:
        name (str): Cryptocurrency name.
        target_currency (str): Target currency (default: 'usd').

    Returns:
        Optional[float]: Current price or None if not found.
    """
    params = {"ids": name, "vs_currencies": target_currency}
    data = fetch_data_from_api("simple/price", params)
    if data and name in data:
        return data[name].get(target_currency)

    logger.error(f"Price data for {name} in {target_currency} not found.")
    return None


def cache_cryptos_in_db(cursor, cryptos: List[CryptoData]):
    cursor.execute("DELETE FROM cryptocurrencies")  # Clear old data
    for crypto in cryptos:
        cursor.execute(
            """
            INSERT INTO cryptocurrencies (
                name, symbol, image, current_price, market_cap, market_cap_rank,
                fully_diluted_valuation, total_volume, high_24h, low_24h,
                price_change_24h, price_change_percentage_24h, market_cap_change_24h,
                market_cap_change_percentage_24h, circulating_supply, total_supply,
                max_supply, ath, ath_change_percentage, ath_date, atl,
                atl_change_percentage, atl_date, last_updated, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                crypto.name,
                crypto.symbol,
                crypto.image,
                crypto.current_price,
                crypto.market_cap,
                crypto.market_cap_rank,
                crypto.fully_diluted_valuation,
                crypto.total_volume,
                crypto.high_24h,
                crypto.low_24h,
                crypto.price_change_24h,
                crypto.price_change_percentage_24h,
                crypto.market_cap_change_24h,
                crypto.market_cap_change_percentage_24h,
                crypto.circulating_supply,
                crypto.total_supply,
                crypto.max_supply,
                crypto.ath,
                crypto.ath_change_percentage,
                crypto.ath_date,
                crypto.atl,
                crypto.atl_change_percentage,
                crypto.atl_date,
                crypto.last_updated,
                datetime.now().isoformat(),
            ),
        )


def get_top_1000_crypto() -> List[Dict[str, Any]]:
    """
    Fetch the top 1000 cryptocurrencies by market cap.

    Returns:
        List[Dict[str, Any]]: List of cryptocurrency data.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if is_cache_valid(cursor, "SELECT MAX(timestamp) FROM cryptocurrencies", ()):
        logger.info("Using cached data from SQLite.")
        cursor.execute("SELECT * FROM cryptocurrencies")
        cryptos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return cryptos

    logger.info("Fetching data from CoinGecko API.")
    all_cryptos = []
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 250,
        "sparkline": "false",
        "price_change_percentage": "24h",
    }

    for page in range(1, 5):
        params["page"] = page
        data = fetch_data_from_api("coins/markets", params)
        if data:
            validated_data = validate_crypto_data(data)
            all_cryptos.extend(validated_data)
        else:
            logger.error(f"Error fetching data from page {page}.")
            break

    cache_cryptos_in_db(cursor, all_cryptos)
    conn.commit()
    conn.close()

    return [crypto.model_dump() for crypto in all_cryptos]


def fetch_gainers_and_losers_owned(
    user_id: int, owned_coins: List[str]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Fetch the top gainers and losers for owned coins with caching.

    Args:
        user_id (int): User ID.
        owned_coins (List[str]): List of owned coin IDs.

    Returns:
        Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]: Gainers and losers.
    """
    if not owned_coins:
        logger.info("No owned coins provided.")
        return [], []

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check cache validity
            if is_cache_valid(
                cursor,
                "SELECT timestamp FROM gainers_losers_cache WHERE user_id = ? AND owned_coins = ?",
                (user_id, ",".join(owned_coins)),
            ):
                logger.info("Using cached gainers/losers data.")
                cursor.execute(SELECT_CACHE_QUERY, (user_id, ",".join(owned_coins)))
                result = cursor.fetchone()
                if result:
                    return json.loads(result[0]), json.loads(result[1])

            # Fetch data from API
            logger.info("Fetching gainers and losers from API.")
            params = {
                "vs_currency": "usd",
                "ids": ",".join(owned_coins),
                "order": "market_cap_desc",
                "per_page": len(owned_coins),
                "price_change_percentage": "24h",
            }
            data = fetch_data_from_api("coins/markets", params)
            if not data:
                logger.error("Failed to fetch data from API.")
                return [], []

            # Filter and sort data
            filtered_data = [
                coin
                for coin in data
                if coin.get("price_change_percentage_24h") is not None
            ]
            gainers = sorted(
                filtered_data,
                key=lambda x: x["price_change_percentage_24h"],
                reverse=True,
            )
            losers = sorted(
                filtered_data, key=lambda x: x["price_change_percentage_24h"]
            )

            # Cache results
            cursor.execute(DELETE_CACHE_QUERY, (user_id, ",".join(owned_coins)))
            cursor.execute(
                INSERT_CACHE_QUERY,
                (
                    user_id,
                    ",".join(owned_coins),
                    json.dumps(gainers),
                    json.dumps(losers),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

            return gainers, losers
    except Exception as e:
        logger.error(f"Error fetching gainers and losers: {e}")
        return [], []
