from flask import Blueprint, jsonify, request, current_app
from app.services.api_football import APIFootballService
from app.services.data_processor import DataProcessor
from app.ml.predictor import Predictor
from app.ml.backtester import Backtester

data_collection_bp = Blueprint("data_collection", __name__)


@data_collection_bp.route("/collect", methods=["POST"])
def collect_data():
    data = request.get_json() or {}
    season = data.get("season", 2025)

    if not current_app.config.get("API_FOOTBALL_KEY"):
        return jsonify({"error": "API_FOOTBALL_KEY não configurada no .env"}), 400

    try:
        api = APIFootballService()
        processor = DataProcessor()

        # Garantir que a liga existe
        league_api_id = current_app.config["BRASILEIRAO_LEAGUE_ID"]
        processor.ensure_league(league_api_id)

        print(f"Coletando dados da temporada {season}...")
        fixtures = api.collect_season_data(season)
        print(f"Coletadas {len(fixtures)} partidas com estatísticas")

        processed = processor.process_season_data(fixtures, league_api_id, season)

        # Coletar jogos futuros
        print(f"Coletando jogos futuros da temporada {season}...")
        upcoming = api.collect_upcoming_fixtures(season)
        upcoming_processed = processor.process_upcoming_fixtures(upcoming, league_api_id, season)
        print(f"Coletados {upcoming_processed} jogos futuros")

        return jsonify({
            "message": f"Temporada {season} coletada com sucesso",
            "fixtures_collected": len(fixtures),
            "fixtures_processed": processed,
            "upcoming_collected": upcoming_processed,
        })

    except Exception as e:
        return jsonify({"error": f"Erro na coleta: {str(e)}"}), 500


@data_collection_bp.route("/collect/multiple", methods=["POST"])
def collect_multiple_seasons():
    data = request.get_json() or {}
    seasons = data.get("seasons", [2025, 2026])

    if not current_app.config.get("API_FOOTBALL_KEY"):
        return jsonify({"error": "API_FOOTBALL_KEY não configurada no .env"}), 400

    results = []
    for season in seasons:
        try:
            api = APIFootballService()
            processor = DataProcessor()

            league_api_id = current_app.config["BRASILEIRAO_LEAGUE_ID"]
            processor.ensure_league(league_api_id)

            print(f"\nColetando temporada {season}...")
            fixtures = api.collect_season_data(season)
            processed = processor.process_season_data(fixtures, league_api_id, season)

            results.append({
                "season": season,
                "status": "success",
                "fixtures_processed": processed,
            })
        except Exception as e:
            results.append({"season": season, "status": "error", "error": str(e)})

    return jsonify({"results": results})


@data_collection_bp.route("/train", methods=["POST"])
def train_models():
    data = request.get_json() or {}
    seasons = data.get("seasons", [2025, 2026])

    try:
        predictor = Predictor()
        result = predictor.train(seasons)
        return jsonify({"message": "Modelos treinados com sucesso", **result})
    except Exception as e:
        return jsonify({"error": f"Erro no treino: {str(e)}"}), 500


@data_collection_bp.route("/status", methods=["GET"])
def data_status():
    from app.models.database import Match, Team, Season
    from app import db

    total_matches = Match.query.filter(Match.status == "FT").count()
    total_teams = Team.query.count()
    seasons = db.session.query(Season.year).order_by(Season.year).all()

    import os
    models_dir = current_app.config["ML_MODELS_DIR"]
    models_exist = os.path.exists(os.path.join(models_dir, "dixon_coles.joblib"))

    return jsonify({
        "total_matches": total_matches,
        "total_teams": total_teams,
        "seasons": [s.year for s in seasons],
        "models_trained": models_exist,
    })


@data_collection_bp.route("/backtest", methods=["POST"])
def run_backtest():
    data = request.get_json() or {}
    seasons = data.get("seasons", [2025, 2026])

    try:
        backtester = Backtester()
        results = backtester.run(seasons)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": f"Erro no backtesting: {str(e)}"}), 500
