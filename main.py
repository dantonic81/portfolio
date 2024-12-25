import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

from api.api import api
from api.admin_api import admin_api
from api.login_api import login_api
from api.alert_api import alert_api
from api.notification_api import notification_api
from models.database import init_db
from utils.scheduler import configure_scheduler
from services.alerts import check_alerts
from flask_session import Session
from utils.logger import logger


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "./sessions"
app.config["ALERT_CHECK_INTERVAL"] = 2  # Check alerts every 2 minutes
app.config["ALERT_MAX_INSTANCES"] = 2
app.config['UPLOAD_FOLDER'] = './uploads'

Session(app)

app.register_blueprint(api)
app.register_blueprint(admin_api)
app.register_blueprint(login_api)
app.register_blueprint(alert_api)
app.register_blueprint(notification_api)


API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise EnvironmentError("API_KEY is not set in the environment variables.")
logger.info("App is starting...")

try:
    logger.info("Initializing database.")
    init_db()
    logger.info("Database initialized successfully.")
except Exception as e:
    raise RuntimeError(f"Failed to initialize the database: {e}")


try:
    logger.info("Adding jobs to schedule.")
    configure_scheduler(app, check_alerts)
    logger.info("Scheduler configured successfully.")
except Exception as e:
    raise RuntimeError(f"Failed to configure the scheduler: {e}")


# Run the Flask web server on port 8000
if __name__ == "__main__":
    app.run(
        host=os.environ.get("FLASK_HOST", "0.0.0.0"),
        port=int(os.environ.get("FLASK_PORT", 8000)),
    )
