import os
from werkzeug.security import generate_password_hash
from models.db_connection import get_db_connection
from utils.csv_loader import load_portfolio_from_csv, load_transactions_from_csv


# Initialize the SQLite database
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 0,
            is_admin BOOLEAN DEFAULT 0,
            confirmation_token TEXT,
            token_expiry TEXT,
            created_at TEXT DEFAULT (DATETIME('now'))
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            bio TEXT,
            profile_picture TEXT,
            created_at TEXT DEFAULT (DATETIME('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS guest_data (
            session_id TEXT PRIMARY KEY,
            crypto_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            added_at TEXT DEFAULT (DATETIME('now'))
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(user_id),
            name TEXT,
            abbreviation TEXT COLLATE NOCASE,
            amount REAL,
            UNIQUE(user_id, abbreviation COLLATE NOCASE)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cryptocurrencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            symbol TEXT,
            image TEXT,
            current_price REAL,
            market_cap REAL,
            market_cap_rank INTEGER,
            fully_diluted_valuation REAL,
            total_volume REAL,
            high_24h REAL,
            low_24h REAL,
            price_change_24h REAL,
            price_change_percentage_24h REAL,
            market_cap_change_24h REAL,
            market_cap_change_percentage_24h REAL,
            circulating_supply REAL,
            total_supply REAL,
            max_supply REAL,
            ath REAL,
            ath_change_percentage REAL,
            ath_date TEXT,
            atl REAL,
            atl_change_percentage REAL,
            atl_date TEXT,
            last_updated TEXT,
            timestamp TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(user_id),
            date TEXT NOT NULL,
            portfolio_value DECIMAL(20, 2) NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, date)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gainers_losers_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(user_id),
            owned_coins TEXT,
            gainers TEXT,
            losers TEXT,
            timestamp TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(user_id),
            name TEXT NOT NULL,
            abbreviation TEXT NOT NULL,
            transaction_date TEXT NOT NULL,
            amount REAL NOT NULL,
            price REAL NOT NULL,
            transaction_id TEXT UNIQUE NOT NULL,
            rate REAL NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(user_id),
            name TEXT NOT NULL,
            cryptocurrency TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            threshold REAL NOT NULL,
            created_at TEXT DEFAULT (DATETIME('now')), -- Stores ISO 8601 format timestamp
            status TEXT DEFAULT 'active'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(user_id),
            alert_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notification_text TEXT NOT NULL,
            current_price REAL NOT NULL,
            is_read BOOLEAN DEFAULT 0,
            FOREIGN KEY (alert_id) REFERENCES alerts(id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,              -- e.g., "login_attempt", "registration_attempt"
            username TEXT,                         -- Username entered by the user
            ip_address TEXT,                       -- IP address of the client
            user_agent TEXT,                       -- User-Agent string from the request headers
            status TEXT NOT NULL,                  -- e.g., "success", "failure"
            error_message TEXT,                    -- For recording failure reasons
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP -- Automatically logs the time of the event
        )
    ''')
    conn.commit()

    # Ensure the default admin account exists
    username = os.getenv('ADMIN_USERNAME')
    email = os.getenv('ADMIN_EMAIL')
    password = os.getenv('ADMIN_PASSWORD')
    password_hash = generate_password_hash(password)

    try:
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, is_admin, is_active)
            VALUES (?, ?, ?, 1, 1)
            ON CONFLICT (email) DO NOTHING
        ''', (username, email, password_hash))
        conn.commit()

        # Fetch the user_id of the default admin
        cursor.execute('SELECT user_id FROM users WHERE email = ?', (email,))
        admin_user_id = cursor.fetchone()[0]
        print(f"Default admin account ensured: {username} ({email}) with user_id {admin_user_id}")
    except Exception as e:
        print(f"Error creating default admin account: {e}")
        admin_user_id = None

    # Check if the portfolio table is empty before loading CSV data and ensure admin exists before loading data
    if admin_user_id:
        cursor.execute('SELECT COUNT(*) FROM portfolio')
        portfolio_count = cursor.fetchone()[0]

        if portfolio_count == 0:
            print("Loading portfolio data from CSV...")
            load_portfolio_from_csv('crypto_portfolio.csv', admin_user_id)
        else:
            print("Portfolio data already loaded.")

        # Check if the transactions table is empty before loading CSV data
        cursor.execute('SELECT COUNT(*) FROM transactions')
        transactions_count = cursor.fetchone()[0]

        if transactions_count == 0:
            print("Loading transactions data from CSV...")
            load_transactions_from_csv('crypto_transactions.csv', admin_user_id)
        else:
            print("Transactions data already loaded.")

    else:
        print("Admin user not created; skipping data load.")

    conn.close()