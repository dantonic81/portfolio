import csv
import os

from flask import Blueprint, jsonify, request, render_template, session, redirect, current_app
from dateutil.parser import parse

from models.db_connection import get_db_cursor
from services.portfolio import (
    get_assets_by_query,
    read_portfolio,
    calculate_portfolio_value,
    fetch_owned_coins_from_db,
)
import sqlite3
from utils.coingecko import get_top_1000_crypto, fetch_gainers_and_losers_owned
from utils.anomaly_detection import detect_outliers, combine_results, preprocess_data
from datetime import datetime
from utils.logger import logger
from utils.login_required import login_required
from math import ceil
from werkzeug.utils import secure_filename


api = Blueprint("api", __name__)


@api.route("/search_assets", methods=["GET"])
@login_required
def search_assets():
    query = request.args.get("query")  # Get the query parameter from the request
    user_id = session["user_id"]
    if query:
        assets = get_assets_by_query(
            query, user_id
        )  # Function to fetch assets based on the query
        return jsonify({"assets": assets})  # Send the result back as JSON
    else:
        return jsonify({"assets": []})  # Return empty if no query is provided


@api.route("/portfolio/filter_by_letter", methods=["GET"])
@login_required
def filter_assets_by_letter():
    letter = request.args.get(
        "letter", ""
    ).upper()  # Defaults to empty string if not provided
    logger.debug(f"Filtering assets by letter: {letter}")  # Add this log

    if not letter or len(letter) != 1 or not letter.isalpha():
        return (
            jsonify(
                {
                    "error": "Invalid letter parameter. Please provide a single alphabet character."
                }
            ),
            400,
        )

    user_id = session["user_id"]

    # Query the portfolio for assets whose names start with the specified letter
    cursor, conn = get_db_cursor()
    if cursor is None:
        return jsonify({"error": "Database connection failed"}), 500

    cursor.execute(
        """SELECT name, abbreviation, amount FROM portfolio WHERE name LIKE ? AND user_id = ?""",
        (f"{letter}%", user_id),
    )
    filtered_assets = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Return filtered assets as JSON
    return jsonify(filtered_assets)


@api.route("/update_asset", methods=["POST"])
@login_required
def update_asset():
    try:
        # Parse data from the request
        data = request.get_json()
        asset_id = data.get("id")  # Asset ID to identify which record to update
        new_amount = data.get("amount")  # New amount to update

        if not asset_id or new_amount is None:
            return jsonify({"success": False, "message": "Invalid data provided"}), 400

        user_id = session["user_id"]

        cursor, conn = get_db_cursor()
        if cursor is None:
            return jsonify({"error": "Database connection failed"}), 500

        # Update the asset in the database
        cursor.execute(
            """
            UPDATE portfolio
            SET amount = ?
            WHERE id = ? AND user_id = ?
        """,
            (float(new_amount), int(asset_id), user_id),
        )

        conn.commit()
        conn.close()

        # Check if the update was successful
        if cursor.rowcount == 0:
            return jsonify({"success": False, "message": "Asset not found"}), 404

        return jsonify({"success": True, "message": "Asset updated successfully"}), 200

    except sqlite3.Error as e:
        # Handle database errors
        logger.error(f"SQLite error: {e}")
        return jsonify({"success": False, "message": "Database error occurred"}), 500

    except Exception as e:
        # Handle other unexpected errors
        logger.error(f"Error in update_asset: {e}")
        return (
            jsonify({"success": False, "message": "An unexpected error occurred"}),
            500,
        )


@api.route("/delete_asset", methods=["POST"])
@login_required
def delete_asset():
    try:
        # Parse data from the request
        data = request.get_json()
        asset_id = data.get("id")  # Asset ID to identify which record to delete

        if not asset_id:
            return jsonify({"success": False, "message": "Invalid data provided"}), 400

        user_id = session["user_id"]

        cursor, conn = get_db_cursor()
        if cursor is None:
            return jsonify({"error": "Database connection failed"}), 500

        # Delete the asset from the database
        cursor.execute(
            """
            DELETE FROM portfolio
            WHERE id = ? AND user_id = ?
        """,
            (int(asset_id), user_id),
        )

        conn.commit()
        conn.close()

        # Check if the delete operation affected any rows
        if cursor.rowcount == 0:
            return jsonify({"success": False, "message": "Asset not found"}), 404

        return jsonify({"success": True, "message": "Asset deleted successfully"}), 200

    except sqlite3.Error as e:
        # Handle database errors
        logger.error(f"SQLite error: {e}")
        return jsonify({"success": False, "message": "Database error occurred"}), 500

    except Exception as e:
        # Handle other unexpected errors
        logger.error(f"Error in delete_asset: {e}")
        return (
            jsonify({"success": False, "message": "An unexpected error occurred"}),
            500,
        )


@api.route("/save_portfolio_value", methods=["POST"])
@login_required
def save_portfolio_value():
    try:
        user_id = session["user_id"]
        portfolio = read_portfolio(user_id)  # Assuming this reads your portfolio data
        top_1000_cryptos = (
            get_top_1000_crypto()
        )  # Assuming this gets the top 1000 cryptos

        # Calculate the total portfolio value
        total_portfolio_value = calculate_portfolio_value(portfolio, top_1000_cryptos)

        # Get today's date
        today_date = datetime.now().strftime("%Y-%m-%d")

        # Connect to the database and check for an existing record
        cursor, conn = get_db_cursor()
        if cursor is None:
            return jsonify({"error": "Database connection failed"}), 500

        cursor.execute(
            "SELECT portfolio_value FROM portfolio_daily WHERE user_id = ? AND date = ?",
            (user_id, today_date),
        )
        existing_record = cursor.fetchone()

        if existing_record:
            # If the portfolio value for today already exists, check if it's different
            existing_value = existing_record[0]
            if existing_value != total_portfolio_value:
                # Update the portfolio value if it's different
                cursor.execute(
                    """
                    UPDATE portfolio_daily
                    SET portfolio_value = ?
                    WHERE user_id = ? AND date = ?
                """,
                    (total_portfolio_value, user_id, today_date),
                )

                conn.commit()
                conn.close()

                return jsonify(
                    {
                        "success": True,
                        "message": "Portfolio value updated successfully.",
                    }
                )
            else:
                # If the value is the same, log a warning and return success
                logger.warning(
                    f"Portfolio value for today ({today_date}) is the same as the previous value."
                )
                conn.close()
                return jsonify(
                    {
                        "success": True,
                        "message": "Portfolio value is the same for today. No update required.",
                    }
                )

        # If no record exists for today, insert a new record
        cursor.execute(
            """
            INSERT INTO portfolio_daily (user_id, date, portfolio_value)
            VALUES (?, ?, ?)
        """,
            (user_id, today_date, total_portfolio_value),
        )

        conn.commit()
        conn.close()

        return jsonify(
            {"success": True, "message": "Portfolio value saved successfully."}
        )

    except Exception as e:
        logger.error(f"Error while saving portfolio value: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api.route("/get-owned-coins", methods=["GET"])
@login_required
def get_owned_coins():
    try:
        user_id = session["user_id"]
        # Fetch owned coins from your database
        portfolio = read_portfolio(user_id)
        return jsonify(portfolio)
    except Exception as e:
        logger.error(f"Error fetching owned coins: {e}")  # More detailed logging
        return jsonify({"error": "Failed to fetch owned coins"}), 500


@api.route("/market", methods=["GET"])
@login_required
def market_data():
    # Get the current page, items per page, and search term
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 100, type=int)
    search = request.args.get("search", "", type=str).lower()

    cryptos = get_top_1000_crypto()

    # Filter cryptos if search term is provided
    if search:
        cryptos = [
            crypto
            for crypto in cryptos
            if search in crypto["name"].lower() or search in crypto["symbol"].lower()
        ]

    # Calculate the total number of pages
    total_cryptos = len(cryptos)
    total_pages = ceil(total_cryptos / per_page)

    # Apply pagination
    start = (page - 1) * per_page
    end = start + per_page
    paginated_cryptos = cryptos[start:end]

    # Format data as needed
    for coin in paginated_cryptos:
        coin["ath_date"] = parse(coin["ath_date"])
        coin["atl_date"] = parse(coin["atl_date"])
        coin["last_updated"] = parse(coin["last_updated"])
        coin["price_change_percentage_24h"] = coin["price_change_percentage_24h"] or 0
        coin["max_supply"] = coin["max_supply"] or 0
        coin["high_24h"] = coin["high_24h"] or 0
        coin["low_24h"] = coin["low_24h"] or 0
        coin["price_change_24h"] = coin["price_change_24h"] or 0
        coin["market_cap_change_24h"] = coin["market_cap_change_24h"] or 0
        coin["market_cap_change_percentage_24h"] = (
            coin["market_cap_change_percentage_24h"] or 0
        )
        coin["fully_diluted_valuation"] = coin["fully_diluted_valuation"] or 0

    return render_template(
        "market.html",
        coins=paginated_cryptos,
        page=page,
        total_pages=total_pages,
        search=search,
    )


@api.context_processor
def inject_total_portfolio_value():
    user_id = session["user_id"]
    portfolio = read_portfolio(user_id)
    top_1000_cryptos = get_top_1000_crypto()
    total_portfolio_value = calculate_portfolio_value(portfolio, top_1000_cryptos)
    return {"total_portfolio_value": total_portfolio_value}


# Route to show portfolio in HTML format
@api.route("/portfolio", methods=["GET"])
@login_required
def show_portfolio():
    user_id = session["user_id"]
    portfolio = read_portfolio(user_id)
    top_1000_cryptos = get_top_1000_crypto()
    total_portfolio_value = calculate_portfolio_value(portfolio, top_1000_cryptos)

    # Portfolio allocation
    for asset in portfolio:
        allocation = (
            (asset["value"] / total_portfolio_value) * 100
            if total_portfolio_value > 0
            else 0
        )
        asset["allocation_percentage"] = round(allocation, 2)

    portfolio = sorted(portfolio, key=lambda x: x["value"], reverse=True)

    return render_template(
        "portfolio.html",
        portfolio=portfolio,
        total_portfolio_value=total_portfolio_value,
    )


@api.route("/unowned", methods=["GET"])
@login_required
def show_unowned_cryptos():
    user_id = session["user_id"]
    # Read the portfolio and get the top 100 cryptos from CoinGecko
    portfolio = read_portfolio(user_id)
    top_1000_cryptos = get_top_1000_crypto()
    top_100_cryptos = top_1000_cryptos[:100]  # Get only the top 100

    # Create a set of owned crypto names and abbreviations from the portfolio
    owned_cryptos = {asset["name"].lower() for asset in portfolio}
    owned_cryptos.update({asset["abbreviation"].upper() for asset in portfolio})

    # Compare with the top 100 and find the missing ones
    missing_cryptos = []
    for crypto in top_100_cryptos:
        name = crypto["name"].lower()
        abbreviation = crypto["symbol"].upper()
        if name not in owned_cryptos and abbreviation not in owned_cryptos:
            missing_cryptos.append(
                {
                    "name": crypto["name"],
                    "abbreviation": crypto["symbol"],
                    "rank": crypto["market_cap_rank"],
                    "current_price": crypto["current_price"],
                    "image": crypto["image"],
                }
            )

    # Sort the missing cryptos by rank for easier viewing
    missing_cryptos = sorted(missing_cryptos, key=lambda x: x["rank"])

    return render_template("unowned.html", missing_cryptos=missing_cryptos)


@api.route("/")
def index():
    try:
        if "user_id" not in session:
            return redirect("/login")  # Redirect to login if not logged in

        # Validate that user exists in the database
        cursor, conn = get_db_cursor()
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (session["user_id"],))
        user_exists = cursor.fetchone()

        if not user_exists:
            session.clear()  # Clear invalid session
            return redirect("/login")  # Redirect to login

        # Extract the user_id from session
        user_id = session["user_id"]

        # Fetch owned coins
        owned_coins = fetch_owned_coins_from_db(user_id)

        # If no owned coins, return empty lists for gainers and losers
        if not owned_coins:
            gainers, losers = [], []
        else:
            # Fetch gainers and losers
            gainers, losers = fetch_gainers_and_losers_owned(user_id, owned_coins)

        # Fetch the portfolio data that we need for calculation
        portfolio = read_portfolio(user_id)  # Your function to read portfolio data
        top_1000_cryptos = get_top_1000_crypto()  # Function to get the top 1000 cryptos

        # Calculate the total portfolio value
        total_portfolio_value = calculate_portfolio_value(portfolio, top_1000_cryptos)

        # Get today's date for checking the database
        today_date = datetime.now().strftime("%Y-%m-%d")

        # Connect to the database and check if a record for today already exists
        cursor, conn = get_db_cursor()
        if cursor is None:
            return jsonify({"error": "Database connection failed"}), 500

        # Calculate the sum of all investments in the transactions table
        cursor.execute(
            "SELECT SUM(price) FROM transactions WHERE user_id = ?", (user_id,)
        )
        sum_price = cursor.fetchone()[0]
        total_investment = round(sum_price, 2) if sum_price is not None else 0

        # If there's no sum (i.e., no records), set total_investment to 0
        if total_investment is None:
            total_investment = 0

        # Calculate Nominal ROI
        if total_investment > 0:
            nominal_roi = (
                (total_portfolio_value - total_investment) / total_investment
            ) * 100
        else:
            nominal_roi = 0
        formatted_nominal_roi = f"{nominal_roi:+.2f}%"

        cursor.execute(
            "SELECT 1 FROM portfolio_daily WHERE date = ? AND user_id = ?",
            (today_date, user_id),
        )
        existing_record = cursor.fetchone()

        if existing_record:
            # If the record exists, update the portfolio_value
            cursor.execute(
                """
                UPDATE portfolio_daily
                SET portfolio_value = ?
                WHERE date = ? AND user_id = ?
            """,
                (total_portfolio_value, today_date, user_id),
            )
        else:
            # If no record for today, insert the new portfolio_value
            cursor.execute(
                """
                INSERT INTO portfolio_daily (user_id, date, portfolio_value)
                VALUES (?, ?, ?)
            """,
                (user_id, today_date, total_portfolio_value),
            )

        conn.commit()

        # Fetch the previous day's portfolio value from the database for percentage change calculation
        cursor.execute(
            """
            SELECT portfolio_value
            FROM portfolio_daily
            WHERE user_id = ?
            ORDER BY date DESC
            LIMIT 2
        """,
            (user_id,),
        )
        records = cursor.fetchall()
        conn.close()

        # Assign values for the current and previous portfolio values
        current_value = total_portfolio_value  # Use the freshly calculated value
        previous_value = (
            records[1][0] if len(records) > 1 else current_value
        )  # Last saved value

        # Calculate percentage change dynamically
        percentage_change = (
            ((current_value - previous_value) / previous_value) * 100
            if previous_value
            else 0
        )

        # Format the percentage change for display
        formatted_percentage_change = f"{percentage_change:+.2f}%"

        # Pass raw and formatted values to the template
        return render_template(
            "index.html",
            total_portfolio_value=current_value,
            percentage_change=percentage_change,  # Raw value
            formatted_percentage_change=formatted_percentage_change,  # Display string
            total_investment=total_investment,
            nominal_roi=nominal_roi,
            formatted_nominal_roi=formatted_nominal_roi,
            gainers=gainers,
            losers=losers,
        )

    except Exception as e:
        logger.error(f"Error while fetching portfolio data: {e}")
        return render_template(
            "index.html",
            total_portfolio_value=0,
            percentage_change=0,
            formatted_percentage_change="0.00%",
            total_investment=0,
        )


@api.route("/outliers", methods=["GET"])
@login_required
def show_outliers():
    user_id = session["user_id"]
    # Fetch owned coins
    owned_coins = fetch_owned_coins_from_db(user_id)

    # Fetch gainers and losers
    gainers, losers = fetch_gainers_and_losers_owned(user_id, owned_coins)

    if not gainers and not losers:
        return "Failed to fetch data from the API.", 500

    # Preprocess data
    features, coin_ids = preprocess_data(gainers, losers)

    # Detect outliers using Isolation Forest
    labels = detect_outliers(features, contamination=0.1)

    # Combine API data with model results
    results = combine_results(labels, gainers, losers)

    return render_template(
        "outliers.html",
        outlier_cryptos=results["outliers"],
        inlier_cryptos=results["inliers"],
    )


@api.route("/add_asset", methods=["POST"])
@login_required
def add_asset():
    # Log that the request has been received
    logger.debug("Received POST request at '/add_asset'")

    try:
        # Get data from the request as JSON
        data = request.get_json()
        logger.debug("Received data: %s", data)  # Log the received data

        name = data.get("name").strip().lower()
        abbreviation = data.get("abbreviation").strip().lower()
        amount = float(data.get("amount"))  # Ensure the amount is a float
        user_id = session["user_id"]

        # Connect to SQLite and check if the asset already exists
        cursor, conn = get_db_cursor()
        if cursor is None:
            return jsonify({"error": "Database connection failed"}), 500

        # Query to check for existing asset by name or abbreviation
        cursor.execute(
            """
                SELECT * FROM portfolio
                WHERE user_id = ? AND (name = ? OR abbreviation = ?)
            """,
            (user_id, name, abbreviation),
        )
        existing_asset = cursor.fetchone()

        if existing_asset:
            logger.warning("Asset already exists: %s", existing_asset)
            conn.close()
            return jsonify({"success": False, "error": "Asset already exists!"}), 400

        # Insert the new asset if it doesn't exist
        cursor.execute(
            """
                INSERT INTO portfolio (user_id, name, abbreviation, amount)
                VALUES (?, ?, ?, ?)
            """,
            (user_id, name.capitalize(), abbreviation.upper(), amount),
        )

        conn.commit()
        conn.close()

        logger.debug("Asset added successfully.")  # Log success
        return jsonify({"success": True})

    except Exception as e:
        # Log any error that occurs
        logger.error("Error while adding asset: %s", e)
        return jsonify({"success": False, "error": str(e)})


@api.route("/portfolio/add", methods=["POST"])
@login_required
def add_to_portfolio():
    user_id = session["user_id"]
    data = request.json
    name = data.get("name")
    abbreviation = data.get("abbreviation")
    amount = data.get("amount")

    if not name or not abbreviation or not amount or amount <= 0:
        return jsonify({"success": False, "error": "Invalid input"}), 400

    try:
        cursor, conn = get_db_cursor()

        # Insert into portfolio
        cursor.execute(
            """
            INSERT INTO portfolio (user_id, name, abbreviation, amount)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, abbreviation)
            DO UPDATE SET amount = portfolio.amount + excluded.amount
        """,
            (user_id, name, abbreviation.upper(), amount),
        )

        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


ALLOWED_EXTENSIONS = {'csv'}



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@api.route('/upload_csv', methods=['POST'])
def upload_csv():
    user_id = session["user_id"]
    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    if 'csvFile' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['csvFile']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        try:
            # Open the database connection
            cursor, conn = get_db_cursor()

            # Process the CSV file
            with open(filepath, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # Insert each row into the transactions table
                    cursor.execute('''
                        INSERT INTO transactions (
                            user_id, name, abbreviation, transaction_date, 
                            amount, price, transaction_id, rate
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        user_id, row['name'], row['abbreviation'], row['transaction_date'],
                        float(row['amount']), float(row['price']), row['transaction_id'], float(row['rate'])
                    ))

            conn.commit()
            conn.close()
            os.remove(filepath)

            return jsonify({'message': 'File successfully processed'}), 200

        except Exception as e:
            conn.rollback()
            conn.close()
            os.remove(filepath)
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'Invalid file type'}), 400
