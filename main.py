import os
from flask import Flask
from dotenv import load_dotenv
from api.api import api
from models.database import init_db


load_dotenv()

app = Flask(__name__)

app.register_blueprint(api)


API_KEY = os.environ.get("API_KEY")
# API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise EnvironmentError("API_KEY is not set in the environment variables.")

init_db()

# Run the Flask web server on port 8000
if __name__ == '__main__':
    # init_db()
    app.run(host='0.0.0.0', port=8000)
