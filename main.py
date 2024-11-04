import csv
import requests

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

# Usage
portfolio = read_portfolio('crypto_portfolio.csv')

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

# Fetch top 100 crypto data
top_100_cryptos = get_top_100_crypto()

def calculate_portfolio_value(portfolio, top_100):
    # Map to find current price by symbol
    price_lookup = {crypto['symbol'].upper(): crypto['current_price'] for crypto in top_100}

    total_value = 0.0
    for asset in portfolio:
        symbol = asset['abbreviation']
        amount = asset['amount']
        current_price = price_lookup.get(symbol, 0)  # Default to 0 if not found
        asset_value = amount * current_price
        asset['current_price'] = current_price
        asset['value'] = asset_value
        total_value += asset_value

    return total_value

# Calculate total portfolio value and update portfolio data with current price and value
total_portfolio_value = calculate_portfolio_value(portfolio, top_100_cryptos)

# Display portfolio with metrics
print("Your Portfolio:")
for asset in portfolio:
    print(f"{asset['name']} ({asset['abbreviation']}):")
    print(f"  Amount: {asset['amount']}")
    print(f"  Current Price: ${asset['current_price']}")
    print(f"  Value: ${asset['value']}")

print(f"\nTotal Portfolio Value: ${total_portfolio_value}")

# Calculate and display percentage allocation
print("\nPortfolio Allocation:")
for asset in portfolio:
    allocation = (asset['value'] / total_portfolio_value) * 100 if total_portfolio_value > 0 else 0
    print(f"{asset['name']} ({asset['abbreviation']}): {allocation:.2f}% of portfolio")
