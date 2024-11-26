import csv
import requests
import sqlite3
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from sklearn.ensemble import IsolationForest
import pandas as pd
import json
import numpy as np
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)


# Setup logging to see what happens in the console
logging.basicConfig(level=logging.DEBUG)
DATABASE = 'crypto_portfolio.db'
CACHE_EXPIRY = 120  # Cache expiry time in seconds
API_KEY = os.environ.get("API_KEY")
# API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise EnvironmentError("API_KEY is not set in the environment variables.")


# Helper function to connect to SQLite
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# Initialize the SQLite database
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            abbreviation TEXT UNIQUE COLLATE NOCASE,
            amount REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cryptocurrencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            symbol TEXT,
            current_price REAL,
            market_cap_rank INTEGER,
            timestamp TEXT,
            image TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            portfolio_value DECIMAL(20, 2) NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gainers_losers_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owned_coins TEXT,
            gainers TEXT,
            losers TEXT,
            timestamp TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            abbreviation TEXT NOT NULL,
            transaction_date TEXT NOT NULL,
            amount REAL NOT NULL,
            price REAL NOT NULL,
            transaction_id TEXT UNIQUE NOT NULL,
            rate REAL NOT NULL
        )
    ''')

    conn.commit()

    # Check if the portfolio table is empty before loading CSV data
    cursor.execute('SELECT COUNT(*) FROM portfolio')
    portfolio_count = cursor.fetchone()[0]
    # print(portfolio_count)

    if portfolio_count == 0:
        print("Loading portfolio data from CSV...")
        load_portfolio_from_csv('crypto_portfolio.csv')
    else:
        print("Portfolio data already loaded.")

    # Check if the transactions table is empty before loading CSV data
    cursor.execute('SELECT COUNT(*) FROM transactions')
    transactions_count = cursor.fetchone()[0]
    # print(transactions_count)

    if transactions_count == 0:
        print("Loading transactions data from CSV...")
        load_transactions_from_csv('crypto_transactions.csv')
    else:
        print("Portfolio data already loaded.")


    conn.close()


# Load portfolio data from CSV into SQLite (One-time operation)
def load_portfolio_from_csv(csv_file_path):
    conn = get_db_connection()
    cursor = conn.cursor()

    with open(csv_file_path, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            cursor.execute('''
                INSERT INTO portfolio (name, abbreviation, amount)
                VALUES (?, ?, ?)
            ''', (row['name'], row['abbreviation'].upper(), float(row['amount'])))

    conn.commit()
    conn.close()


# Load transactions data from CSV into SQLite (One-time operation)
def load_transactions_from_csv(csv_file_path):
    conn = get_db_connection()
    cursor = conn.cursor()

    with open(csv_file_path, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            cursor.execute('''
                INSERT INTO transactions (name, abbreviation, transaction_date, amount, price, transaction_id, rate)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (row['name'],
                row['abbreviation'].upper(),
                row['transaction_date'],
                float(row['amount']),
                float(row['price']),
                row['transaction_id'],
                float(row['rate'])
            ))

    conn.commit()
    conn.close()



# Fetch portfolio from SQLite
def read_portfolio():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, abbreviation, amount FROM portfolio')
    portfolio = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return portfolio


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

    all_cryptos = []  # List to store all results

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
            INSERT INTO cryptocurrencies (name, symbol, current_price, market_cap_rank, timestamp, image)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            crypto['name'],
            crypto['symbol'],
            crypto['current_price'],
            crypto['market_cap_rank'],
            datetime.now().isoformat(),
            crypto['image']
        ))
    conn.commit()
    conn.close()

    return all_cryptos



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


def fetch_gainers_and_losers_owned(owned_coins):
    """
    Fetch the top gainers and losers for owned coins with caching.

    Args:
        owned_coins (list): List of coin IDs owned (e.g., ["bitcoin", "ethereum", "dogecoin"]).

    Returns:
        tuple: (list of gainers, list of losers)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if cached data exists and is still valid
    cursor.execute('SELECT timestamp FROM gainers_losers_cache WHERE owned_coins = ?', (",".join(owned_coins),))
    result = cursor.fetchone()

    if result:
        cached_timestamp = result[0]
        last_cache_time = datetime.fromisoformat(cached_timestamp)

        if (datetime.now() - last_cache_time).total_seconds() < CACHE_EXPIRY:
            print("Using cached data.")
            cursor.execute('SELECT gainers, losers FROM gainers_losers_cache WHERE owned_coins = ?',
                           (",".join(owned_coins),))
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
        filtered_data = [{**coin, 'symbol': coin['symbol'].lstrip('@')}
                         for coin in data if coin.get("price_change_percentage_24h") is not None]

        # Sort by price change percentage (24h)
        gainers = sorted(filtered_data, key=lambda x: x["price_change_percentage_24h"], reverse=True)
        losers = sorted(filtered_data, key=lambda x: x["price_change_percentage_24h"])

        # Cache the new data in SQLite
        cursor.execute('''
            DELETE FROM gainers_losers_cache WHERE owned_coins = ?
        ''', (",".join(owned_coins),))

        # Store the gainers and losers as text for later retrieval
        cursor.execute('''
            INSERT INTO gainers_losers_cache (owned_coins, gainers, losers, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (
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

def preprocess_data(gainers, losers):
    features = []
    coin_ids = []

    for coin in gainers + losers:
        # Access 'current_price' directly instead of 'usd'
        price = coin.get('current_price', 0)  # Default to 0 if not available

        features.append([
            price,
            coin.get("market_cap", 0),
            coin.get("total_volume", 0)
        ])

        coin_ids.append(coin.get("id", "unknown"))

    return features, coin_ids



def detect_outliers(features, contamination=0.1):
    """
    Use Isolation Forest to detect outliers.

    Args:
        features (numpy.ndarray): Numerical features for the model.
        contamination (float): The proportion of outliers in the data.

    Returns:
        numpy.ndarray: Array of anomaly labels (-1 for outliers, 1 for inliers).
    """
    model = IsolationForest(contamination=contamination, random_state=42)
    model.fit(features)
    labels = model.predict(features)
    return labels


def make_hashable(coin):
    """Recursively convert dictionaries to hashable tuples."""
    if isinstance(coin, dict):
        return tuple((k, make_hashable(v)) for k, v in coin.items())  # Recursively convert dicts
    elif isinstance(coin, list):
        return tuple(make_hashable(v) for v in coin)  # Recursively convert lists
    else:
        return coin  # Return primitive values as they are (e.g., strings, numbers)


def combine_results(labels, coin_ids, gainers, losers):
    combined = gainers + losers

    # Remove duplicates by converting dictionaries to hashable tuples
    seen = set()
    unique_combined = []
    filtered_labels = []  # A list to store the filtered labels corresponding to unique_combined

    for i, coin in enumerate(combined):
        # Extracting and formatting key fields for caching
        formatted_coin = {
            'id': coin.get('id', 'N/A'),
            'name': coin.get('name', 'N/A'),
            'rank': coin.get('market_cap_rank', 'N/A'),
            'current_price': coin.get('current_price', 'N/A'),
            'percentage_gain': coin.get('price_change_percentage_24h', 'N/A'),
            'market_cap': coin.get('market_cap', 'N/A'),
            'volume': coin.get('total_volume', 'N/A'),
            'image': coin.get('image', 'N/A')
        }

        coin_tuple = make_hashable(formatted_coin)  # Convert the formatted coin dictionary to a hashable tuple

        if coin_tuple not in seen:
            seen.add(coin_tuple)
            unique_combined.append(formatted_coin)
            filtered_labels.append(labels[i])  # Keep the corresponding label

    # Now combine again with labels
    outliers = [unique_combined[i] for i, label in enumerate(filtered_labels) if label == -1]
    inliers = [unique_combined[i] for i, label in enumerate(filtered_labels) if label == 1]

    return {"outliers": outliers, "inliers": inliers}


@app.context_processor
def inject_total_portfolio_value():
    portfolio = read_portfolio()
    top_1000_cryptos = get_top_1000_crypto()
    total_portfolio_value = calculate_portfolio_value(portfolio, top_1000_cryptos)
    return {'total_portfolio_value': total_portfolio_value}


# Route to show portfolio in HTML format
@app.route('/portfolio', methods=['GET'])
def show_portfolio():
    portfolio = read_portfolio()
    top_1000_cryptos = get_top_1000_crypto()
    total_portfolio_value = calculate_portfolio_value(portfolio, top_1000_cryptos)

    # Portfolio allocation
    for asset in portfolio:
        allocation = (asset['value'] / total_portfolio_value) * 100 if total_portfolio_value > 0 else 0
        asset['allocation_percentage'] = round(allocation, 2)

    portfolio = sorted(portfolio, key=lambda x: x['value'], reverse=True)

    return render_template('portfolio.html', portfolio=portfolio, total_portfolio_value=total_portfolio_value)


@app.route('/unowned', methods=['GET'])
def show_unowned_cryptos():
    # Read the portfolio and get the top 100 cryptos from CoinGecko
    portfolio = read_portfolio()
    top_1000_cryptos = get_top_1000_crypto()
    top_100_cryptos = top_1000_cryptos[:100]  # Get only the top 100

    # Create a set of owned crypto names and abbreviations from the portfolio
    owned_cryptos = {asset['name'].lower() for asset in portfolio}
    owned_cryptos.update({asset['abbreviation'].upper() for asset in portfolio})

    # Compare with the top 100 and find the missing ones
    missing_cryptos = []
    for crypto in top_100_cryptos:
        name = crypto['name'].lower()
        abbreviation = crypto['symbol'].upper()
        if name not in owned_cryptos and abbreviation not in owned_cryptos:
            missing_cryptos.append({
                'name': crypto['name'],
                'abbreviation': crypto['symbol'],
                'rank': crypto['market_cap_rank'],
                'current_price': crypto['current_price'],
                'image': crypto['image']
            })

    # Sort the missing cryptos by rank for easier viewing
    missing_cryptos = sorted(missing_cryptos, key=lambda x: x['rank'])

    return render_template('unowned.html', missing_cryptos=missing_cryptos)


@app.route('/')
def index():
    try:
        # Fetch owned coins
        owned_coins = fetch_owned_coins_from_db()

        # Fetch gainers and losers
        gainers, losers = fetch_gainers_and_losers_owned(owned_coins)

        # Fetch the portfolio data that we need for calculation
        portfolio = read_portfolio()  # Your function to read portfolio data
        top_1000_cryptos = get_top_1000_crypto()  # Function to get the top 1000 cryptos

        # Calculate the total portfolio value
        total_portfolio_value = calculate_portfolio_value(portfolio, top_1000_cryptos)

        # Get today's date for checking the database
        today_date = datetime.now().strftime('%Y-%m-%d')

        # Connect to the database and check if a record for today already exists
        conn = get_db_connection()
        cursor = conn.cursor()

        # Calculate the sum of all investments in the transactions table
        cursor.execute('SELECT SUM(price) FROM transactions')
        total_investment = round(cursor.fetchone()[0], 2)  # Fetch the sum of prices

        # If there's no sum (i.e., no records), set total_investment to 0
        if total_investment is None:
            total_investment = 0

        # Calculate Nominal ROI
        nominal_roi = ((total_portfolio_value - total_investment) / total_investment) * 100
        formatted_nominal_roi = f"{nominal_roi:+.2f}%"

        cursor.execute('SELECT 1 FROM portfolio_daily WHERE date = ?', (today_date,))
        existing_record = cursor.fetchone()

        if existing_record:
            # If the record exists, update the portfolio_value
            cursor.execute('''
                UPDATE portfolio_daily 
                SET portfolio_value = ? 
                WHERE date = ?
            ''', (total_portfolio_value, today_date))
        else:
            # If no record for today, insert the new portfolio_value
            cursor.execute('''
                INSERT INTO portfolio_daily (date, portfolio_value) 
                VALUES (?, ?)
            ''', (today_date, total_portfolio_value))

        conn.commit()

        # Fetch the previous day's portfolio value from the database for percentage change calculation
        cursor.execute('''
            SELECT portfolio_value 
            FROM portfolio_daily 
            ORDER BY date DESC 
            LIMIT 2
        ''')
        records = cursor.fetchall()
        conn.close()

        # Assign values for the current and previous portfolio values
        current_value = total_portfolio_value  # Use the freshly calculated value
        previous_value = records[1][0] if len(records) > 1 else current_value  # Last saved value

        # Calculate percentage change dynamically
        percentage_change = ((current_value - previous_value) / previous_value) * 100 if previous_value else 0

        # Format the percentage change for display
        formatted_percentage_change = f"{percentage_change:+.2f}%"

        # Pass raw and formatted values to the template
        return render_template(
            'index.html',
            total_portfolio_value=current_value,
            percentage_change=percentage_change,  # Raw value
            formatted_percentage_change=formatted_percentage_change,  # Display string
            total_investment = total_investment,
            nominal_roi=nominal_roi,
            formatted_nominal_roi=formatted_nominal_roi,
            gainers=gainers,
            losers=losers
        )

    except Exception as e:
        app.logger.error(f"Error while fetching portfolio data: {e}")
        return render_template('index.html', total_portfolio_value=0, percentage_change=0, formatted_percentage_change="0.00%", total_investment=0)


@app.route('/outliers', methods=['GET'])
def show_outliers():
    # Fetch owned coins
    owned_coins = fetch_owned_coins_from_db()
    # print("Owned Coins:", owned_coins)  # Debugging line

    # Fetch gainers and losers
    gainers, losers = fetch_gainers_and_losers_owned(owned_coins)

    if not gainers and not losers:
        return "Failed to fetch data from the API.", 500

    # Preprocess data
    features, coin_ids = preprocess_data(gainers, losers)

    # Detect outliers using Isolation Forest
    labels = detect_outliers(features, contamination=0.1)

    # Combine API data with model results
    results = combine_results(labels, coin_ids, gainers, losers)

    return render_template(
        'outliers.html',
        outlier_cryptos=results["outliers"],
        inlier_cryptos=results["inliers"]
    )


@app.route('/add_asset', methods=['POST'])
def add_asset():
    # Log that the request has been received
    app.logger.debug("Received POST request at '/add_asset'")

    try:
        # Get data from the request as JSON
        data = request.get_json()
        app.logger.debug("Received data: %s", data)  # Log the received data

        name = data.get('name').strip().lower()
        abbreviation = data.get('abbreviation').strip().lower()
        amount = float(data.get('amount'))  # Ensure the amount is a float

        # Connect to SQLite and check if the asset already exists
        conn = sqlite3.connect('crypto_portfolio.db')
        cursor = conn.cursor()

        # Query to check for existing asset by name or abbreviation
        cursor.execute('''
                SELECT * FROM portfolio
                WHERE name = ? OR abbreviation = ?
            ''', (name, abbreviation))
        existing_asset = cursor.fetchone()

        if existing_asset:
            app.logger.warning("Asset already exists: %s", existing_asset)
            conn.close()
            return jsonify({"success": False, "error": "Asset already exists!"}), 400

        # Insert the new asset if it doesn't exist
        cursor.execute('''
                INSERT INTO portfolio (name, abbreviation, amount)
                VALUES (?, ?, ?)
            ''', (name, abbreviation, amount))

        conn.commit()
        conn.close()

        app.logger.debug("Asset added successfully.")  # Log success
        return jsonify({"success": True})

    except Exception as e:
        # Log any error that occurs
        app.logger.error("Error while adding asset: %s", e)
        return jsonify({"success": False, "error": str(e)})


def get_assets_by_query(query):
    with sqlite3.connect('crypto_portfolio.db') as conn:
        cursor = conn.cursor()

        # Use parameterized queries to prevent SQL injection
        cursor.execute("SELECT id, name, amount FROM portfolio WHERE name LIKE ?", ('%' + query + '%',))
        assets = cursor.fetchall()

    # Return the results in a structured format (list of dictionaries)
    return [{'id': asset[0], 'asset_name': asset[1], 'amount': asset[2]} for asset in assets]



@app.route('/search_assets', methods=['GET'])
def search_assets():
    query = request.args.get('query')  # Get the query parameter from the request
    if query:
        assets = get_assets_by_query(query)  # Function to fetch assets based on the query
        return jsonify({'assets': assets})  # Send the result back as JSON
    else:
        return jsonify({'assets': []})  # Return empty if no query is provided


@app.route('/portfolio/filter_by_letter', methods=['GET'])
def filter_assets_by_letter():
    letter = request.args.get('letter', '').upper()  # Defaults to empty string if not provided
    app.logger.debug(f"Filtering assets by letter: {letter}")  # Add this log

    if not letter or len(letter) != 1 or not letter.isalpha():
        return jsonify({"error": "Invalid letter parameter. Please provide a single alphabet character."}), 400

    # Query the portfolio for assets whose names start with the specified letter
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''SELECT name, abbreviation, amount FROM portfolio WHERE name LIKE ?''', (f'{letter}%',))
    filtered_assets = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Return filtered assets as JSON
    return jsonify(filtered_assets)


@app.route('/update_asset', methods=['POST'])
def update_asset():
    try:
        # Parse data from the request
        data = request.get_json()
        asset_id = data.get('id')  # Asset ID to identify which record to update
        new_amount = data.get('amount')  # New amount to update

        if not asset_id or new_amount is None:
            return jsonify({'success': False, 'message': 'Invalid data provided'}), 400

        # Connect to the database and update the specified asset
        conn = get_db_connection()
        cursor = conn.cursor()

        # Update the asset in the database
        cursor.execute('''
            UPDATE portfolio
            SET amount = ?
            WHERE id = ?
        ''', (float(new_amount), int(asset_id)))

        conn.commit()
        conn.close()

        # Check if the update was successful
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'message': 'Asset not found'}), 404

        return jsonify({'success': True, 'message': 'Asset updated successfully'}), 200

    except sqlite3.Error as e:
        # Handle database errors
        app.logger.error(f"SQLite error: {e}")
        return jsonify({'success': False, 'message': 'Database error occurred'}), 500

    except Exception as e:
        # Handle other unexpected errors
        app.logger.error(f"Error in update_asset: {e}")
        return jsonify({'success': False, 'message': 'An unexpected error occurred'}), 500


@app.route('/delete_asset', methods=['POST'])
def delete_asset():
    try:
        # Parse data from the request
        data = request.get_json()
        asset_id = data.get('id')  # Asset ID to identify which record to delete

        if not asset_id:
            return jsonify({'success': False, 'message': 'Invalid data provided'}), 400

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Delete the asset from the database
        cursor.execute('''
            DELETE FROM portfolio
            WHERE id = ?
        ''', (int(asset_id),))

        conn.commit()
        conn.close()

        # Check if the delete operation affected any rows
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'message': 'Asset not found'}), 404

        return jsonify({'success': True, 'message': 'Asset deleted successfully'}), 200

    except sqlite3.Error as e:
        # Handle database errors
        app.logger.error(f"SQLite error: {e}")
        return jsonify({'success': False, 'message': 'Database error occurred'}), 500

    except Exception as e:
        # Handle other unexpected errors
        app.logger.error(f"Error in delete_asset: {e}")
        return jsonify({'success': False, 'message': 'An unexpected error occurred'}), 500


@app.route('/save_portfolio_value', methods=['POST'])
def save_portfolio_value():
    try:
        portfolio = read_portfolio()  # Assuming this reads your portfolio data
        top_1000_cryptos = get_top_1000_crypto()  # Assuming this gets the top 1000 cryptos

        # Calculate the total portfolio value
        total_portfolio_value = calculate_portfolio_value(portfolio, top_1000_cryptos)

        # Get today's date
        today_date = datetime.now().strftime('%Y-%m-%d')

        # Connect to the database and check for an existing record
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT portfolio_value FROM portfolio_daily WHERE date = ?', (today_date,))
        existing_record = cursor.fetchone()

        if existing_record:
            # If the portfolio value for today already exists, check if it's different
            existing_value = existing_record[0]
            if existing_value != total_portfolio_value:
                # Update the portfolio value if it's different
                cursor.execute('''
                    UPDATE portfolio_daily 
                    SET portfolio_value = ? 
                    WHERE date = ?
                ''', (total_portfolio_value, today_date))

                conn.commit()
                conn.close()

                return jsonify({"success": True, "message": "Portfolio value updated successfully."})
            else:
                # If the value is the same, log a warning and return success
                app.logger.warning(f"Portfolio value for today ({today_date}) is the same as the previous value.")
                conn.close()
                return jsonify({"success": True, "message": "Portfolio value is the same for today. No update required."})

        # If no record exists for today, insert a new record
        cursor.execute('''
            INSERT INTO portfolio_daily (date, portfolio_value) 
            VALUES (?, ?)
        ''', (today_date, total_portfolio_value))

        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "Portfolio value saved successfully."})

    except Exception as e:
        app.logger.error(f"Error while saving portfolio value: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


init_db()

# Run the Flask web server on port 8000
if __name__ == '__main__':
    # init_db()
    app.run(host='0.0.0.0', port=8000, debug=True)
