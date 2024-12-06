import csv
from models.db_connection import get_db_connection


# Load portfolio data from CSV into SQLite (One-time operation)
def load_portfolio_from_csv(csv_file_path, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    with open(csv_file_path, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            cursor.execute('''
                INSERT INTO portfolio (user_id, name, abbreviation, amount)
                VALUES (?, ?, ?, ?)
            ''', (user_id, row['name'], row['abbreviation'].upper(), float(row['amount'])))

    conn.commit()
    conn.close()


# Load transactions data from CSV into SQLite (One-time operation)
def load_transactions_from_csv(csv_file_path, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    with open(csv_file_path, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            cursor.execute('''
                INSERT INTO transactions (user_id, name, abbreviation, transaction_date, amount, price, transaction_id, rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                row['name'],
                row['abbreviation'].upper(),
                row['transaction_date'],
                float(row['amount']),
                float(row['price']),
                row['transaction_id'],
                float(row['rate'])
            ))

    conn.commit()
    conn.close()
