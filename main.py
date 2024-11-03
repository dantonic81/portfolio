import csv

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
print(portfolio)



import requests

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

# Usage
top_100_cryptos = get_top_100_crypto()
print(top_100_cryptos)  # Print first 5 for testing

def find_missing_cryptos(portfolio, top_100):
    portfolio_symbols = {item['abbreviation'] for item in portfolio}
    missing_cryptos = [crypto for crypto in top_100 if crypto['symbol'].upper() not in portfolio_symbols]
    return missing_cryptos

# Usage
missing_cryptos = find_missing_cryptos(portfolio, top_100_cryptos)
print("Missing Cryptos in Portfolio:")
for crypto in missing_cryptos:
    print(f"{crypto['name']} ({crypto['symbol'].upper()}) - ${crypto['current_price']}")
