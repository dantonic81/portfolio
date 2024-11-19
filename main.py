import csv
import requests
import sqlite3
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

DATABASE = 'crypto_portfolio.db'
CACHE_EXPIRY = 120  # Cache expiry time in seconds


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
            abbreviation TEXT,
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
            timestamp TEXT
        )
    ''')

    conn.commit()

    # Check if the portfolio table is empty before loading CSV data
    cursor.execute('SELECT COUNT(*) FROM portfolio')
    portfolio_count = cursor.fetchone()[0]
    print(portfolio_count)

    if portfolio_count == 0:
        print("Loading portfolio data from CSV...")
        load_portfolio_from_csv('crypto_portfolio.csv')
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


# Fetch portfolio from SQLite
def read_portfolio():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT name, abbreviation, amount FROM portfolio')
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
            INSERT INTO cryptocurrencies (name, symbol, current_price, market_cap_rank, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            crypto['name'],
            crypto['symbol'],
            crypto['current_price'],
            crypto['market_cap_rank'],
            datetime.now().isoformat()
        ))
    conn.commit()
    conn.close()

    return all_cryptos



def calculate_portfolio_value(portfolio, top_1000):
    # Build a lookup dictionary for fast access by both name and symbol
    price_lookup = {
        crypto['name'].lower(): {'price': crypto['current_price'], 'rank': crypto['market_cap_rank']}
        for crypto in top_1000
    }

    # Add symbol-based lookup as a fallback
    price_lookup.update({
        crypto['symbol'].upper(): {'price': crypto['current_price'], 'rank': crypto['market_cap_rank']}
        for crypto in top_1000
    })

    total_value = 0.0
    for asset in portfolio:
        name = asset['name'].lower()
        symbol = asset['abbreviation']
        amount = asset['amount']

        # Try to look up by name first, then fallback to symbol
        crypto_data = price_lookup.get(name) or price_lookup.get(symbol, {'price': 0, 'rank': None})

        current_price = crypto_data['price']
        asset_value = amount * current_price

        asset['current_price'] = current_price
        asset['value'] = round(asset_value, 8)
        asset['rank'] = crypto_data['rank']

        total_value += asset_value

    return round(total_value, 2)


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
    allocation_data = []
    for asset in portfolio:
        allocation = (asset['value'] / total_portfolio_value) * 100 if total_portfolio_value > 0 else 0
        allocation_data.append({
            'name': asset['name'],
            'abbreviation': asset['abbreviation'],
            'allocation_percentage': round(allocation, 2),
            'value': asset['value'],
            'rank': asset['rank']
        })

    allocation_data = sorted(allocation_data, key=lambda x: x['value'], reverse=True)
    portfolio = sorted(portfolio, key=lambda x: x['value'], reverse=True)

    return render_template('portfolio.html', portfolio=portfolio, total_portfolio_value=total_portfolio_value,
                           allocation_data=allocation_data)


# Route to show portfolio value in JSON format
@app.route('/portfolio/json', methods=['GET'])
def get_portfolio_value():
    portfolio = read_portfolio()
    top_1000_cryptos = get_top_1000_crypto()
    total_portfolio_value = calculate_portfolio_value(portfolio, top_1000_cryptos)

    portfolio_data = []
    for asset in portfolio:
        portfolio_data.append({
            'name': asset['name'],
            'abbreviation': asset['abbreviation'],
            'amount': asset['amount'],
            'current_price': asset['current_price'],
            'value': asset['value'],
            'rank': asset['rank']
        })

    portfolio_data = sorted(portfolio_data, key=lambda x: x['value'], reverse=True)

    return jsonify({
        'portfolio': portfolio_data,
        'total_portfolio_value': total_portfolio_value
    })


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
                'current_price': crypto['current_price']
            })

    # Sort the missing cryptos by rank for easier viewing
    missing_cryptos = sorted(missing_cryptos, key=lambda x: x['rank'])

    return render_template('unowned.html', missing_cryptos=missing_cryptos)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/outliers', methods=['GET'])
def show_outlier_cryptos():
    outlier_cryptos = []
    return render_template('outliers.html', outlier_cryptos=outlier_cryptos)


# Setup logging to see what happens in the console
logging.basicConfig(level=logging.DEBUG)

@app.route('/add_asset', methods=['POST'])
def add_asset():
    # Log that the request has been received
    app.logger.debug("Received POST request at '/add_asset'")

    try:
        # Get data from the request as JSON
        data = request.get_json()
        app.logger.debug("Received data: %s", data)  # Log the received data

        name = data.get('name')
        abbreviation = data.get('abbreviation')
        amount = float(data.get('amount'))  # Ensure the amount is a float

        # Connect to SQLite and insert data into the portfolio table
        conn = sqlite3.connect('crypto_portfolio.db')
        cursor = conn.cursor()

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

# Run the Flask web server on port 8000
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8000, debug=True)
