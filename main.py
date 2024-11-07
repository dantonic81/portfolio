import csv
import requests
from flask import Flask, jsonify

app = Flask(__name__)

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

def get_top_100_crypto():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 100,
        'page': 1,
        'sparkline': 'false'
    }
    response = requests.get(url, params=params)
    return response.json()

def calculate_portfolio_value(portfolio, top_100):
    price_lookup = {crypto['symbol'].upper(): crypto['current_price'] for crypto in top_100}

    total_value = 0.0
    for asset in portfolio:
        symbol = asset['abbreviation']
        amount = asset['amount']
        current_price = price_lookup.get(symbol, 0)
        asset_value = amount * current_price
        asset['current_price'] = current_price
        asset['value'] = asset_value
        total_value += asset_value

    return total_value

# Route to show portfolio value in JSON format
@app.route('/portfolio', methods=['GET'])
def get_portfolio_value():
    portfolio = read_portfolio('crypto_portfolio.csv')
    top_100_cryptos = get_top_100_crypto()
    total_portfolio_value = calculate_portfolio_value(portfolio, top_100_cryptos)

    # Adding the portfolio data to the response
    portfolio_data = []
    for asset in portfolio:
        portfolio_data.append({
            'name': asset['name'],
            'abbreviation': asset['abbreviation'],
            'amount': asset['amount'],
            'current_price': asset['current_price'],
            'value': asset['value']
        })

    return jsonify({
        'portfolio': portfolio_data,
        'total_portfolio_value': total_portfolio_value
    })

# Route for the portfolio allocation
@app.route('/portfolio/allocation', methods=['GET'])
def get_portfolio_allocation():
    portfolio = read_portfolio('crypto_portfolio.csv')
    top_100_cryptos = get_top_100_crypto()
    total_portfolio_value = calculate_portfolio_value(portfolio, top_100_cryptos)

    allocation_data = []
    for asset in portfolio:
        allocation = (asset['value'] / total_portfolio_value) * 100 if total_portfolio_value > 0 else 0
        allocation_data.append({
            'name': asset['name'],
            'abbreviation': asset['abbreviation'],
            'allocation_percentage': round(allocation, 2)
        })

    return jsonify({'allocation': allocation_data})

# Run the Flask web server on port 8000
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
