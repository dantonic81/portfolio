import requests
from datetime import datetime
from models.database import get_db_connection


CACHE_EXPIRY = 120  # Cache expiry time in seconds


# Function to get current price from CoinGecko API
def get_current_price(name, target_currency='usd'):
    url = "https://api.coingecko.com/api/v3/simple/price"

    # Create the query parameters based on the input
    params = {
        'ids': name,  # The cryptocurrency ID (e.g., 'bitcoin', 'ethereum')
        'vs_currencies': target_currency  # The target currency (e.g., 'usd')
    }

    try:
        # Send GET request to the CoinGecko API
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an exception for 4xx/5xx HTTP errors
        data = response.json()  # Parse the JSON response

        # Ensure the data is structured as expected and return the price
        if name in data:
            return data[name].get(target_currency)  # Get the price in the specified currency
        else:
            print(f"Error: No data found for {name} in {target_currency}")
            return None
    except requests.exceptions.RequestException as e:
        # Handle exceptions for network issues, invalid responses, etc.
        print(f"Error fetching price data: {e}")
        return None


def get_top_1000_crypto():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if cache exists and is valid
    cursor.execute('SELECT MAX(timestamp) FROM cryptocurrencies')
    result = cursor.fetchone()
    cached_timestamp = result[0]  # This will be in ISO 8601 format

    if cached_timestamp:
        # Convert to datetime for comparison
        last_cache_time = datetime.fromisoformat(cached_timestamp)
        if (datetime.now() - last_cache_time).total_seconds() < CACHE_EXPIRY:
            print("Using cached data from SQLite.")
            cursor.execute('SELECT * FROM cryptocurrencies')
            cryptos = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return cryptos

    print("Fetching data from CoinGecko API.")
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 250,
        'sparkline': 'false',
        'price_change_percentage': '24h'
    }

    all_cryptos = []

    for page in range(1, 5):
        params['page'] = page
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            all_cryptos.extend(data)
        else:
            print(f"Error fetching data from page {page}. Status Code: {response.status_code}")
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


def fetch_gainers_and_losers_owned(user_id, owned_coins):
    """
    Fetch the top gainers and losers for owned coins with caching.

    Args:
        :param owned_coins: List of coin IDs owned (e.g., ["bitcoin", "ethereum", "dogecoin"]).
        :param user_id:

    Returns:
        tuple: (list of gainers, list of losers)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if cached data exists and is still valid
    cursor.execute('SELECT timestamp FROM gainers_losers_cache WHERE user_id = ? AND owned_coins = ?', (user_id, ",".join(owned_coins)))
    result = cursor.fetchone()

    if result:
        cached_timestamp = result[0]
        last_cache_time = datetime.fromisoformat(cached_timestamp)

        if (datetime.now() - last_cache_time).total_seconds() < CACHE_EXPIRY:
            print("Using cached data.")
            cursor.execute('SELECT gainers, losers FROM gainers_losers_cache WHERE user_id = ? AND owned_coins = ?',
                           (user_id, ",".join(owned_coins)))
            cached_data = cursor.fetchone()
            conn.close()
            # Return the cached gainers and losers (they are stored as text, so need to be evaluated)
            return eval(cached_data[0]), eval(cached_data[1])

    print("Fetching data from CoinGecko API.")
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": ",".join(owned_coins),
        "order": "market_cap_desc",
        "per_page": len(owned_coins),
        "price_change_percentage": "24h",
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Filter out coins where price_change_percentage_24h is None
        filtered_data = [{**coin, 'name': coin['name'].lstrip('@'), 'symbol': coin['symbol'].replace('@', '')}
                         for coin in data if coin.get("price_change_percentage_24h") is not None]

        # Sort by price change percentage (24h)
        gainers = sorted(filtered_data, key=lambda x: x["price_change_percentage_24h"], reverse=True)
        losers = sorted(filtered_data, key=lambda x: x["price_change_percentage_24h"])

        # Cache the new data in SQLite
        cursor.execute('''
            DELETE FROM gainers_losers_cache WHERE user_id = ? AND owned_coins = ?
        ''', (user_id, ",".join(owned_coins)))

        # Store the gainers and losers as text for later retrieval
        cursor.execute('''
            INSERT INTO gainers_losers_cache (user_id, owned_coins, gainers, losers, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            user_id,
            ",".join(owned_coins),
            str(gainers),  # Store as text
            str(losers),  # Store as text
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

        return gainers, losers

    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        conn.close()
        return [], []
