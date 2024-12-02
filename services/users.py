from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

def register_user(username, email, password):
    hashed_password = generate_password_hash(password)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
        ''', (username, email, hashed_password))
        conn.commit()
        print("User registered successfully!")
    except sqlite3.IntegrityError as e:
        print(f"Error: {e}")
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('SELECT password_hash FROM users WHERE username = ?', (username,))
    row = cursor.fetchone()

    if row and check_password_hash(row[0], password):
        print("Login successful!")
    else:
        print("Invalid username or password.")
    conn.close()