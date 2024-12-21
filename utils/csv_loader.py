import csv
from models.db_connection import get_db_connection
from utils.logger import logger


def load_data_from_csv(csv_file_path: str, query: str, params_func: callable) -> None:
    """
    Generic function to load data from a CSV file into a database.

    Args:
        csv_file_path (str): Path to the CSV file.
        query (str): SQL query for inserting data.
        params_func (callable): Function to extract parameters from a row.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        with open(csv_file_path, mode="r") as file:
            reader = csv.DictReader(file)
            rows = [params_func(row) for row in reader]

        cursor.executemany(query, rows)
        conn.commit()
        logger.info(f"Successfully inserted {len(rows)} records from {csv_file_path}.")

    except Exception as e:
        logger.error(f"Error loading data from {csv_file_path}: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def load_portfolio_from_csv(csv_file_path: str, user_id: int) -> None:
    """
    Load portfolio data from a CSV file into the database.

    Args:
        csv_file_path (str): Path to the portfolio CSV file.
        user_id (int): ID of the user the data belongs to.
    """

    def params(row):
        return user_id, row["name"], row["abbreviation"].upper(), float(row["amount"])

    query = """
        INSERT INTO portfolio (user_id, name, abbreviation, amount)
        VALUES (?, ?, ?, ?)
    """
    load_data_from_csv(csv_file_path, query, params)


def load_transactions_from_csv(csv_file_path: str, user_id: int) -> None:
    """
    Load transaction data from a CSV file into the database.

    Args:
        csv_file_path (str): Path to the transactions CSV file.
        user_id (int): ID of the user the data belongs to.
    """

    def params(row):
        return (
            user_id,
            row["name"],
            row["abbreviation"].upper(),
            row["transaction_date"],
            float(row["amount"]),
            float(row["price"]),
            row["transaction_id"],
            float(row["rate"]),
        )

    query = """
        INSERT INTO transactions (user_id, name, abbreviation, transaction_date, amount, price, transaction_id, rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    load_data_from_csv(csv_file_path, query, params)
