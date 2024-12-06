import os
from flask import Flask
from dotenv import load_dotenv
from api.api import api
from api.admin_api import admin_api
from api.login_api import login_api
from api.alert_api import alert_api
from api.notification_api import notification_api
from models.database import init_db
from utils.scheduler import configure_scheduler
from services.alerts import check_alerts
from flask_session import Session


load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './sessions'
Session(app)

app.register_blueprint(api)
app.register_blueprint(admin_api)
app.register_blueprint(login_api)
app.register_blueprint(alert_api)
app.register_blueprint(notification_api)


API_KEY = os.environ.get("API_KEY")
# API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise EnvironmentError("API_KEY is not set in the environment variables.")

# initialize the database and create default admin
init_db()

# Configure the scheduler
configure_scheduler(app, check_alerts)  # Pass your app and the function to the scheduler


# Run the Flask web server on port 8000
if __name__ == '__main__':
    # init_db()
    app.run(host='0.0.0.0', port=8000)
