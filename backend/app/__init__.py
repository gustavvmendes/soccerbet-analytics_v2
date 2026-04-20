from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config.from_object("app.config.Config")

    CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})
    db.init_app(app)

    from app.routes.matches import matches_bp
    from app.routes.predictions import predictions_bp
    from app.routes.data_collection import data_collection_bp
    from app.routes.live import live_bp

    app.register_blueprint(matches_bp, url_prefix="/api/matches")
    app.register_blueprint(predictions_bp, url_prefix="/api/predictions")
    app.register_blueprint(data_collection_bp, url_prefix="/api/data")
    app.register_blueprint(live_bp, url_prefix="/api/live")

    with app.app_context():
        db.create_all()

    return app
