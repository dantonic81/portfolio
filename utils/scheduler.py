from flask_apscheduler import APScheduler
from utils.logger import logger
from flask import Flask
from typing import Callable


def configure_scheduler(app: Flask, check_alerts_func: Callable) -> None:
    """
    Configures and starts the APScheduler for the Flask application.

    Args:
        app (Flask): The Flask application instance.
        check_alerts_func (Callable[[], None]): The function to be scheduled.
            Must take no arguments and return None.

    Raises:
        Exception: If an error occurs during scheduler initialization or job addition.
    """
    scheduler = APScheduler()
    app.config["SCHEDULER_API_ENABLED"] = True
    try:
        scheduler.init_app(app)
        scheduler.add_job(
            id="check_alerts",
            func=check_alerts_func,
            trigger="interval",
            minutes=int(app.config.get("ALERT_CHECK_INTERVAL", 1)),
            replace_existing=True,
            max_instances=int(app.config.get("ALERT_MAX_INSTANCES", 1)),
        )
        scheduler.start()
        logger.info("Scheduler started and 'check_alerts' job added successfully.")

    except Exception as e:
        logger.error(f"Failed to initialize the scheduler: {e}")
        raise
