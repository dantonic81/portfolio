from flask import Blueprint, request, render_template, flash, url_for, redirect, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models.db_connection import get_db_cursor
from services.email import send_email
from utils.auditing import log_audit_event
import uuid
from datetime import datetime, timedelta, timezone

login_api = Blueprint('login_api', __name__)


@login_api.route('/confirm_email')
def confirm_email():
    token = request.args.get('token')
    if not token:
        return "Invalid confirmation link.", 400  # Return an error if no token is provided

    cursor, conn = get_db_cursor()
    if cursor is None:
        return "Database connection failed.", 500

    try:
        cursor.execute('SELECT * FROM users WHERE confirmation_token = ?', (token,))
        user = cursor.fetchone()

        if not user:
            return "Invalid or expired link.", 404

        token_expiry_str = user['token_expiry']
        token_expiry = datetime.strptime(token_expiry_str, '%Y-%m-%d %H:%M:%S.%f%z')
        # Check token expiration11
        if token_expiry < datetime.now(timezone.utc):
            return "Confirmation link has expired.", 400  # If the token is expired

        cursor.execute('UPDATE users SET is_active = 1, confirmation_token = NULL, token_expiry = NULL WHERE confirmation_token = ?', (token,))
        conn.commit()  # Commit the email confirmation update

        return render_template('email_confirmed.html')

    except Exception as e:
        return f"Error confirming email: {str(e)}", 500

    finally:
        conn.close()  # Ensure the connection is closed


@login_api.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Handle form submission (data from an HTML form)
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            log_audit_event(request, 'registration_attempt', username, 'failure', 'Missing required fields')
            return render_template('register.html', error="All fields are required.")

        # Hash the password before storing it
        password_hash = generate_password_hash(password)
        token = str(uuid.uuid4())  # Generate a unique token
        expiration_time = datetime.now(timezone.utc) + timedelta(minutes=5)  # Token expires in 5 minutes

        cursor, conn = get_db_cursor()
        if cursor is None:
            log_audit_event(request, 'registration_attempt', username, 'failure', 'Database connection failed')
            return render_template('register.html', error="Database connection failed.")

        try:
            # Check if email already exists
            cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
            existing_user = cursor.fetchone()

            if existing_user:
                # Token check if token is None or expired
                token_expiry_str = existing_user['token_expiry']
                if not token_expiry_str or datetime.strptime(token_expiry_str, '%Y-%m-%d %H:%M:%S.%f%z') < datetime.now(timezone.utc):
                    # Token expired or missing, delete the user
                    cursor.execute('DELETE FROM users WHERE email = ?', (email,))  # Remove expired user

                    # Generate a new token for the new registration
                    new_token = str(uuid.uuid4())
                    new_expiration_time = datetime.now(timezone.utc) + timedelta(minutes=5)  # New token expires in 5 minutes

                    # Proceed with the new registration
                    cursor.execute(
                        'INSERT INTO users (username, email, password_hash, is_active, confirmation_token, token_expiry) VALUES (?, ?, ?, 0, ?, ?)',
                        (username, email, password_hash, new_token, new_expiration_time))
                    conn.commit()

                    # Send confirmation email for new registration
                    confirm_link = url_for('login_api.confirm_email', token=new_token, email=email, _external=True)
                    email_subject = "Confirm Your Email Address"
                    email_content = f"""<p>Hi {username},</p><p>Please confirm your email by clicking below:</p><a href="{confirm_link}">Confirm Email</a>"""
                    send_email(email, email_subject, email_content)
                    flash('A confirmation email has been sent.', 'success')

                    return redirect(url_for('login_api.login'))
                else:
                    # Token not expired, use the existing one
                    log_audit_event(request, 'registration_attempt', username, 'failure', 'Token not expired')
                    flash("Confirmation link has not expired. Please use the existing link.", 'error')
                    return render_template('register.html', error="Confirmation link has not expired.")
            else:
                # Proceed with the insert if email does not exist
                cursor.execute(
                    '''INSERT INTO users (username, email, password_hash, is_active, confirmation_token, token_expiry) VALUES (?, ?, ?, 0, ?, ?)''',
                    (username, email, password_hash, token, expiration_time))
                conn.commit()  # Commit the transaction to ensure it's saved

                # Send confirmation email
                confirm_link = url_for('login_api.confirm_email', token=token, email=email, _external=True)
                email_subject = "Confirm Your Email Address"
                email_content = f"""<p>Hi {username},</p><p>Please confirm your email by clicking below:</p><a href="{confirm_link}">Confirm Email</a> <p>If you didn’t request this, please ignore this email.</p><p>Best regards,</p><p>Your Crypto Portfolio Team</p>"""
                send_email(email, email_subject, email_content)
                flash('A confirmation email has been sent.', 'success')

                return redirect(url_for('login_api.login'))  # Redirect after successful registration

        except Exception as e:
            log_audit_event(request, 'registration_attempt', username, 'failure', str(e))
            return render_template('register.html', error=str(e))

        finally:
            conn.close()  # Ensure the connection is closed

    # Handle GET request: Render the registration form
    return render_template('register.html')


@login_api.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('api.index'))  # Redirect to dashboard if already logged in

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            log_audit_event(request, 'login_attempt', username, 'failure', 'Username or password missing')
            flash('Username and password are required!', 'error')
            return render_template('login.html')

        cursor, conn = get_db_cursor()
        if cursor is None:
            log_audit_event(request, 'login_attempt', username, 'failure', 'Database connection failed')
            flash('Database connection failed!', 'error')
            return render_template('login.html')

        try:
            # Query for the user by username
            cursor.execute("SELECT username, password_hash, user_id FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()

            if user and check_password_hash(user[1], password):
                session['user_id'] = user[2]  # Store user_id in session, not just username
                session['username'] = user[0]
                log_audit_event(request, 'login_attempt', username, 'success')
                flash('Login successful!', 'success')
                return redirect(url_for('api.index'))  # Replace 'api.index' with your desired endpoint
            else:
                log_audit_event(request, 'login_attempt', username, 'failure', 'Invalid credentials')
                flash('Invalid username or password', 'error')
        except Exception as e:
            log_audit_event(request, 'login_attempt', username, 'failure', str(e))
            flash(f'An error occurred: {str(e)}', 'error')
        finally:
            conn.close()

    return render_template('login.html')


@login_api.route('/logout', methods=['POST'])
def logout():
    # Debugging log: Print the session before logout
    print(session)
    session.clear()
    return jsonify({'message': 'Logout successful!'}), 200
