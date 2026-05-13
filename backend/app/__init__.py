import os

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
    from app.routes.auto_update import auto_update_bp

    app.register_blueprint(matches_bp, url_prefix="/api/matches")
    app.register_blueprint(predictions_bp, url_prefix="/api/predictions")
    app.register_blueprint(data_collection_bp, url_prefix="/api/data")
    app.register_blueprint(live_bp, url_prefix="/api/live")
    app.register_blueprint(auto_update_bp, url_prefix="/api/auto-update")

    with app.app_context():
        db.create_all()
        # Habilitar WAL mode para permitir leituras concorrentes
        with db.engine.connect() as conn:
            conn.execute(db.text("PRAGMA journal_mode=WAL"))
            conn.commit()

    # -- Iniciar atualizacao automatica ao subir --
    # Evitar rodar duas vezes com o reloader do Flask debug mode
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        from app.services.auto_updater import start_startup_update, start_periodic_updates
        start_startup_update(app)
        start_periodic_updates(app, interval_hours=6)

    return app
