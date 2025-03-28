import os
import json
from slack_sdk import WebClient
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from .app import logger

class Config:
    PORT = int(os.environ.get("PORT", 8080))
    SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
    GOOGLE_SHEETS_CREDENTIALS_STR = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
    GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")
    SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "#systems-issues")
    SYSTEM_USERS = os.environ.get("SYSTEM_USERS", "").split(",")
    TIMEZONE = os.environ.get("TIMEZONE", "America/New_York")

    # Validate environment variables
    if not SLACK_BOT_TOKEN:
        logger.error("SLACK_BOT_TOKEN environment variable is not set.")
        raise ValueError("SLACK_BOT_TOKEN environment variable is not set.")
    if not GOOGLE_SHEETS_CREDENTIALS_STR:
        logger.error("GOOGLE_SHEETS_CREDENTIALS environment variable is not set.")
        raise ValueError("GOOGLE_SHEETS_CREDENTIALS environment variable is not set.")
    try:
        GOOGLE_SHEETS_CREDENTIALS = json.loads(GOOGLE_SHEETS_CREDENTIALS_STR)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in GOOGLE_SHEETS_CREDENTIALS: {e}")
        raise ValueError(f"Invalid JSON in GOOGLE_SHEETS_CREDENTIALS: {e}")
    if not GOOGLE_SHEET_ID:
        logger.error("GOOGLE_SHEET_ID environment variable is not set.")
        raise ValueError("GOOGLE_SHEET_ID environment variable is not set.")

# Initialize Slack client
client = WebClient(token=Config.SLACK_BOT_TOKEN)
logger.info("Slack client initialized.")

# Initialize Google Sheets
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(Config.GOOGLE_SHEETS_CREDENTIALS, scope)
    gc = gspread.authorize(creds)
    spreadsheet = gc.open_by_key(Config.GOOGLE_SHEET_ID)
    sheet = spreadsheet.worksheet("TicketLog")
    weekly_counts_sheet = spreadsheet.worksheet("WeeklyCounts")
    logger.info("Google Sheets initialized.")
except Exception as e:
    logger.error(f"Failed to initialize Google Sheets: {e}")
    raise