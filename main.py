import csv
import requests
import time
from flask import Flask, jsonify, render_template

app = Flask(__name__)

# Cache for storing the crypto data and timestamp
crypto_cache = {
    'data': None,
    'timestamp': None
}
CACHE_EXPIRY = 120  # Cache expiry time in seconds


# Original functions
def read_portfolio(csv_file_path):
    portfolio = []
    with open(csv_file_path, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            portfolio.append({
                'name': row['name'],
                'abbreviation': row['abbreviation'].upper(),
                'amount': float(row['amount'])
            })
    return portfolio


def get_top_1000_crypto():
    # Check if cached data exists and is still valid
    if crypto_cache['data'] and (time.time() - crypto_cache['timestamp']) < CACHE_EXPIRY:
        print("Using cached data.")
        return crypto_cache['data']

    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 250,  # Request 250 results per page
        'sparkline': 'false',
        'price_change_percentage': '24h'
    }

    all_cryptos = []  # List to store all results

    # Loop through pages 1 to 4 (to get up to 1000)
    for page in range(1, 5):  # Pages 1 to 4
        params['page'] = page
        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                for index, crypto in enumerate(data, start=1 + (page - 1) * 250):
                    crypto['rank'] = index  # Add rank
                all_cryptos.extend(data)
            else:
                print(f"No data on page {page}.")
                break
        else:
            print(f"Error fetching data from page {page}. Status Code: {response.status_code}")
            break

    # Update cache if we retrieved all 1000 records successfully
    if len(all_cryptos) >= 1000:
        crypto_cache['data'] = all_cryptos
        crypto_cache['timestamp'] = time.time()
        print(f"Cached {len(all_cryptos)} records.")

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

    return total_value


# Route to show portfolio in HTML format
@app.route('/portfolio', methods=['GET'])
def show_portfolio():
    portfolio = read_portfolio('crypto_portfolio.csv')
    top_1000_cryptos = get_top_1000_crypto()
    total_portfolio_value = round(calculate_portfolio_value(portfolio, top_1000_cryptos), 2)

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
    portfolio = read_portfolio('crypto_portfolio.csv')
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
    portfolio = read_portfolio('crypto_portfolio.csv')
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
                'rank': crypto['rank'],
                'current_price': crypto['current_price']
            })

    # Sort the missing cryptos by rank for easier viewing
    missing_cryptos = sorted(missing_cryptos, key=lambda x: x['rank'])

    return render_template('unowned.html', missing_cryptos=missing_cryptos)

@app.route('/outliers', methods=['GET'])
def show_outlier_cryptos():
    outlier_cryptos = []
    return render_template('outliers.html', outlier_cryptos=outlier_cryptos)

# Run the Flask web server on port 8000
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
