from flask import Flask
from config import Config  # ✅ No 'apps.' prefix
from routes import setup_routes
from scheduler import start_scheduler

app = Flask(__name__)
app.config.from_object(Config)

setup_routes(app)
start_scheduler()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
