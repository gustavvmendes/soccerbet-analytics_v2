import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///football_predictions.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
    API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"
    BRASILEIRAO_LEAGUE_ID = 71
    ML_MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ml_models")
