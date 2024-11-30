from flask_apscheduler import APScheduler

def configure_scheduler(app, check_alerts_func):
    scheduler = APScheduler()
    app.config['SCHEDULER_API_ENABLED'] = True
    scheduler.init_app(app)
    scheduler.add_job(
        id='check_alerts',
        func=check_alerts_func,
        trigger='interval',
        minutes=1,
        replace_existing=True,
        max_instances=1
    )
    scheduler.start()