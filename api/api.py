from flask import Blueprint, jsonify, request, render_template
from dateutil.parser import parse
from services.portfolio import get_assets_by_query, read_portfolio, calculate_portfolio_value, fetch_owned_coins_from_db
from models.database import get_db_connection
import sqlite3
from utils.coingecko import get_top_1000_crypto, fetch_gainers_and_losers_owned
from utils.anomaly_detection import detect_outliers, combine_results, preprocess_data
from datetime import datetime
from utils.logger import logger
from services.alerts import get_active_alerts
from math import ceil



api = Blueprint('api', __name__)




@api.route('/search_assets', methods=['GET'])
def search_assets():
    query = request.args.get('query')  # Get the query parameter from the request
    if query:
        assets = get_assets_by_query(query)  # Function to fetch assets based on the query
        return jsonify({'assets': assets})  # Send the result back as JSON
    else:
        return jsonify({'assets': []})  # Return empty if no query is provided


@api.route('/portfolio/filter_by_letter', methods=['GET'])
def filter_assets_by_letter():
    letter = request.args.get('letter', '').upper()  # Defaults to empty string if not provided
    logger.debug(f"Filtering assets by letter: {letter}")  # Add this log

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


@api.route('/update_asset', methods=['POST'])
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
        logger.error(f"SQLite error: {e}")
        return jsonify({'success': False, 'message': 'Database error occurred'}), 500

    except Exception as e:
        # Handle other unexpected errors
        logger.error(f"Error in update_asset: {e}")
        return jsonify({'success': False, 'message': 'An unexpected error occurred'}), 500


@api.route('/delete_asset', methods=['POST'])
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
        logger.error(f"SQLite error: {e}")
        return jsonify({'success': False, 'message': 'Database error occurred'}), 500

    except Exception as e:
        # Handle other unexpected errors
        logger.error(f"Error in delete_asset: {e}")
        return jsonify({'success': False, 'message': 'An unexpected error occurred'}), 500


@api.route('/save_portfolio_value', methods=['POST'])
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
                logger.warning(f"Portfolio value for today ({today_date}) is the same as the previous value.")
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
        logger.error(f"Error while saving portfolio value: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api.route('/get-owned-coins', methods=['GET'])
def get_owned_coins():
    try:
        # Fetch owned coins from your database
        portfolio = read_portfolio()
        return jsonify(portfolio)
    except Exception as e:
        logger.error(f"Error fetching owned coins: {e}")  # More detailed logging
        return jsonify({"error": "Failed to fetch owned coins"}), 500


@api.route('/api/active_alerts', methods=['GET'])
def active_alerts():
    alerts = get_active_alerts()

    # Convert the list of tuples into a list of dictionaries
    column_names = ['id', 'name', 'cryptocurrency', 'alert_type', 'threshold', 'created_at', 'status']
    alert_dicts = []

    for alert in alerts:
        alert_dict = dict(zip(column_names, alert))
        alert_dicts.append(alert_dict)

    return jsonify(alert_dicts)

@api.route('/api/set_alert', methods=['POST'])
def set_alert():
    data = request.json
    print("Received data:", data)

    # Validate the incoming data
    required_fields = ["name", "cryptocurrency", "alert_type", "threshold"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    # Insert the alert into the database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = '''
        INSERT INTO alerts (name, cryptocurrency, alert_type, threshold)
        VALUES (?, ?, ?, ?)
        '''
        cursor.execute(query, (data['name'], data["cryptocurrency"], data["alert_type"], data["threshold"]))
        conn.commit()
        alert_id = cursor.lastrowid  # Get the ID of the newly created alert
        conn.close()

        return jsonify({"message": "Alert set successfully!", "alert_id": alert_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route('/api/alert/<int:alert_id>', methods=['GET'])
def get_alert(alert_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM alerts WHERE id = ?"  # Use '?' placeholder for parameters
    cursor.execute(query, (alert_id,))

    alert = cursor.fetchone()  # Fetch one result, as alert_id should be unique

    if alert:
        column_names = ['id', 'name', 'threshold', 'alert_type', 'status']  # Example column names
        alert_dict = dict(zip(column_names, alert))
        conn.close()
        return jsonify(alert_dict)
    else:
        conn.close()
        return jsonify({"error": "Alert not found"}), 404


# Delete an alert
@api.route('/api/alert/<int:alert_id>', methods=['DELETE'])
def delete_alert(alert_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "DELETE FROM alerts WHERE id = ?"
    cursor.execute(query, (alert_id,))

    conn.commit()
    conn.close()

    return jsonify({"message": "Alert deleted successfully"})


@api.route('/notifications', methods=['GET'])
def get_notifications():
    query = "SELECT * FROM notifications ORDER BY created_at DESC;"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query)
    notifications = cursor.fetchall()
    conn.close()
    # Format notifications into a list of dictionaries for JSON response
    notifications_dict = [
        {
            "id": row[0],
            "alert_id": row[1],
            "notification_text": row[3],  # This should be the actual notification message
            "current_price": row[4],       # This should be the price value
            "is_read": bool(row[5]),       # Ensure this is a boolean
            "created_at": row[2]          # Timestamp field
        }
        for row in notifications
    ]
    return jsonify(notifications_dict)


@api.route('/notifications/<int:notification_id>/mark-read', methods=['POST'])
def mark_notification_as_read(notification_id):
    query = "UPDATE notifications SET is_read = 1 WHERE id = ?;"  # SQLite uses ? as a placeholder
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, (notification_id,))
        conn.commit()
        return jsonify({"message": "Notification marked as read."})
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@api.route('/notifications/unread-count', methods=['GET'])
def get_unread_count():
    query = "SELECT COUNT(*) FROM notifications WHERE is_read = 0;"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query)
    count = cursor.fetchone()[0]
    conn.close()
    return jsonify({"unread_count": count})


@api.route('/market', methods=['GET'])
def market_data():
    # Get the current page, items per page, and search term
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 100, type=int)
    search = request.args.get('search', '', type=str).lower()

    cryptos = get_top_1000_crypto()

    # Filter cryptos if search term is provided
    if search:
        cryptos = [crypto for crypto in cryptos if search in crypto['name'].lower() or search in crypto['symbol'].lower()]

    # Calculate the total number of pages
    total_cryptos = len(cryptos)
    total_pages = ceil(total_cryptos / per_page)

    # Apply pagination
    start = (page - 1) * per_page
    end = start + per_page
    paginated_cryptos = cryptos[start:end]

    # Format data as needed
    for coin in paginated_cryptos:
        coin['ath_date'] = parse(coin['ath_date'])
        coin['atl_date'] = parse(coin['atl_date'])
        coin['last_updated'] = parse(coin['last_updated'])
        coin['price_change_percentage_24h'] = coin['price_change_percentage_24h'] or 0
        coin['max_supply'] = coin['max_supply'] or 0
        coin['high_24h'] = coin['high_24h'] or 0
        coin['low_24h'] = coin['low_24h'] or 0
        coin['price_change_24h'] = coin['price_change_24h'] or 0
        coin['market_cap_change_24h'] = coin['market_cap_change_24h'] or 0
        coin['market_cap_change_percentage_24h'] = coin['market_cap_change_percentage_24h'] or 0
        coin['fully_diluted_valuation'] = coin['fully_diluted_valuation'] or 0

    return render_template('market.html', coins=paginated_cryptos, page=page, total_pages=total_pages, search=search)


@api.context_processor
def inject_total_portfolio_value():
    portfolio = read_portfolio()
    top_1000_cryptos = get_top_1000_crypto()
    total_portfolio_value = calculate_portfolio_value(portfolio, top_1000_cryptos)
    return {'total_portfolio_value': total_portfolio_value}


# Route to show portfolio in HTML format
@api.route('/portfolio', methods=['GET'])
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


@api.route('/unowned', methods=['GET'])
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


@api.route('/')
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
        logger.error(f"Error while fetching portfolio data: {e}")
        return render_template('index.html', total_portfolio_value=0, percentage_change=0, formatted_percentage_change="0.00%", total_investment=0)


@api.route('/outliers', methods=['GET'])
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
    results = combine_results(labels, gainers, losers)

    return render_template(
        'outliers.html',
        outlier_cryptos=results["outliers"],
        inlier_cryptos=results["inliers"]
    )


@api.route('/add_asset', methods=['POST'])
def add_asset():
    # Log that the request has been received
    logger.debug("Received POST request at '/add_asset'")

    try:
        # Get data from the request as JSON
        data = request.get_json()
        logger.debug("Received data: %s", data)  # Log the received data

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
            logger.warning("Asset already exists: %s", existing_asset)
            conn.close()
            return jsonify({"success": False, "error": "Asset already exists!"}), 400

        # Insert the new asset if it doesn't exist
        cursor.execute('''
                INSERT INTO portfolio (name, abbreviation, amount)
                VALUES (?, ?, ?)
            ''', (name, abbreviation, amount))

        conn.commit()
        conn.close()

        logger.debug("Asset added successfully.")  # Log success
        return jsonify({"success": True})

    except Exception as e:
        # Log any error that occurs
        logger.error("Error while adding asset: %s", e)
        return jsonify({"success": False, "error": str(e)})

