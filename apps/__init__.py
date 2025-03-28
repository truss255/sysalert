# system_alert_bot/__init__.py
import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import atexit

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Ensure the logs directory exists
if not os.path.exists('logs'):
    os.makedirs('logs')

handler = RotatingFileHandler('logs/app.log', maxBytes=1000000, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.info("Application initialized.")

# Import configurations
from .config import Config
app.config.from_object(Config)

# Initialize Slack client
from slack_sdk import WebClient
client = WebClient(token=app.config['SLACK_BOT_TOKEN'])
logger.info("Slack client initialized.")

# Initialize Google Sheets
from .config import sheet
logger.info("Google Sheets initialized.")

# Initialize scheduler
scheduler = BackgroundScheduler(timezone=pytz.timezone(app.config['TIMEZONE']))
scheduler.start()
atexit.register(lambda: scheduler.shutdown())
logger.info("Scheduler tasks added.")

# Import routes, helpers, and scheduler tasks
from . import routes, helpers, scheduler

def create_app():
    return app