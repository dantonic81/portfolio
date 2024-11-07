import csv
import requests
from flask import Flask, jsonify, render_template

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


def get_top_1000_crypto():
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

            # Check if the response contains the expected number of coins
            if len(data) > 0:
                all_cryptos.extend(data)  # Add results to the list
            else:
                print(f"No data on page {page}.")
                break
        else:
            print(f"Error fetching data from page {page}. Status Code: {response.status_code}")
            break

    # Verify the total number of results
    print(f"Total results fetched: {len(all_cryptos)}")

    return all_cryptos

def calculate_portfolio_value(portfolio, top_1000):
    price_lookup = {crypto['symbol'].upper(): crypto['current_price'] for crypto in top_1000}

    total_value = 0.0
    for asset in portfolio:
        symbol = asset['abbreviation']
        amount = asset['amount']
        current_price = price_lookup.get(symbol, 0)
        asset_value = amount * current_price
        asset['current_price'] = current_price
        asset['value'] = round(asset_value, 8)
        total_value += asset_value

    return total_value

# Route to show portfolio in HTML format
@app.route('/portfolio', methods=['GET'])
def show_portfolio():
    portfolio = read_portfolio('crypto_portfolio.csv')
    top_1000_cryptos = get_top_1000_crypto()
    print(top_1000_cryptos)  # Check what this variable contains
    total_portfolio_value = round(calculate_portfolio_value(portfolio, top_1000_cryptos), 2)

    # Portfolio allocation
    allocation_data = []
    for asset in portfolio:
        allocation = (asset['value'] / total_portfolio_value) * 100 if total_portfolio_value > 0 else 0
        allocation_data.append({
            'name': asset['name'],
            'abbreviation': asset['abbreviation'],
            'allocation_percentage': round(allocation, 2)
        })

    return render_template('portfolio.html', portfolio=portfolio, total_portfolio_value=total_portfolio_value, allocation_data=allocation_data)

# Route to show portfolio value in JSON format
@app.route('/portfolio/json', methods=['GET'])
def get_portfolio_value():
    portfolio = read_portfolio('crypto_portfolio.csv')
    top_1000_cryptos = get_top_1000_crypto()
    total_portfolio_value = calculate_portfolio_value(portfolio, top_1000_cryptos)

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

# Run the Flask web server on port 8000
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
