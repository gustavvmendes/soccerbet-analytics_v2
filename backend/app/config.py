import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///football_predictions.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # SQLite concurrency: WAL mode + 30s busy timeout
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"timeout": 30},
        "pool_pre_ping": True,
    }
    API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
    API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"
    BRASILEIRAO_LEAGUE_ID = 71
    CURRENT_SEASON = int(os.getenv("CURRENT_SEASON", "2024"))
    ML_MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ml_models")

