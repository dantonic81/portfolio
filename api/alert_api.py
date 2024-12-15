from flask import Blueprint, jsonify, request, session
from models.db_connection import get_db_cursor
from services.alerts import get_active_alerts
from utils.login_required import login_required


alert_api = Blueprint('alert_api', __name__)


@alert_api.route('/api/active_alerts', methods=['GET'])
@login_required
def active_alerts():
    alerts = get_active_alerts()

    # Convert the list of tuples into a list of dictionaries
    column_names = ['id', 'user_id', 'name', 'cryptocurrency', 'alert_type', 'threshold', 'created_at', 'status']
    alert_dicts = []

    for alert in alerts:
        alert_dict = dict(zip(column_names, alert))
        alert_dicts.append(alert_dict)

    return jsonify(alert_dicts)

@alert_api.route('/api/set_alert', methods=['POST'])
@login_required
def set_alert():
    data = request.json
    print("Received data:", data)

    # Validate the incoming data
    required_fields = ["name", "cryptocurrency", "alert_type", "threshold"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    # Retrieve user_id from the session
    user_id = session['user_id']
    if not user_id:
        return jsonify({"error": "User not logged in"}), 401  # Ensure user_id is available


    # Insert the alert into the database
    try:
        cursor, conn = get_db_cursor()
        if cursor is None:
            return jsonify({'error': 'Database connection failed'}), 500

        query = '''
        INSERT INTO alerts (user_id, name, cryptocurrency, alert_type, threshold)
        VALUES (?, ?, ?, ?, ?)
        '''
        cursor.execute(query, (user_id, data['name'], data["cryptocurrency"], data["alert_type"], data["threshold"]))
        conn.commit()
        alert_id = cursor.lastrowid  # Get the ID of the newly created alert
        conn.close()

        return jsonify({"message": "Alert set successfully!", "alert_id": alert_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@alert_api.route('/api/alert/<int:alert_id>', methods=['GET'])
@login_required
def get_alert(alert_id):
    cursor, conn = get_db_cursor()
    if cursor is None:
        return jsonify({'error': 'Database connection failed'}), 500


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
@alert_api.route('/api/alert/<int:alert_id>', methods=['DELETE'])
@login_required
def delete_alert(alert_id):
    # Retrieve user_id from the session
    user_id = session['user_id']
    if not user_id:
        return jsonify({"error": "User not logged in"}), 401

    cursor, conn = get_db_cursor()
    if cursor is None:
        return jsonify({'error': 'Database connection failed'}), 500

    # Check if the alert belongs to the logged-in user
    check_query = "SELECT id FROM alerts WHERE id = ? AND user_id = ?"
    cursor.execute(check_query, (alert_id, user_id))
    alert = cursor.fetchone()

    if not alert:
        return jsonify({"error": "Alert not found or does not belong to the user"}), 404

    query = "DELETE FROM alerts WHERE id = ?"
    cursor.execute(query, (alert_id,))

    conn.commit()
    conn.close()

    return jsonify({"message": "Alert deleted successfully"})