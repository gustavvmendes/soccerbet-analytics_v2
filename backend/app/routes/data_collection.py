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


@data_collection_bp.route("/collect/squads", methods=["POST"])
def collect_squads():
    """Coleta elencos e estatísticas dos jogadores de todos os times."""
    data = request.get_json() or {}
    season = data.get("season", 2026)

    if not current_app.config.get("API_FOOTBALL_KEY"):
        return jsonify({"error": "API_FOOTBALL_KEY não configurada"}), 400

    try:
        api = APIFootballService()
        processor = DataProcessor()

        print(f"Coletando elencos da temporada {season}...")
        all_data = api.collect_all_squads(season)
        result = processor.process_squads_and_stats(all_data, season)

        return jsonify({
            "message": f"Elencos da temporada {season} coletados",
            "players_created": result["players"],
            "stats_processed": result["stats"],
            "teams_collected": len(all_data),
        })
    except Exception as e:
        return jsonify({"error": f"Erro: {str(e)}"}), 500


@data_collection_bp.route("/collect/lineups", methods=["POST"])
def collect_lineups():
    """Coleta escalações de partidas finalizadas."""
    data = request.get_json() or {}
    season = data.get("season", 2026)

    if not current_app.config.get("API_FOOTBALL_KEY"):
        return jsonify({"error": "API_FOOTBALL_KEY não configurada"}), 400

    try:
        api = APIFootballService()
        processor = DataProcessor()

        print(f"Coletando escalações da temporada {season}...")
        lineups = api.collect_lineups_for_matches(season)
        processed = processor.process_lineups(lineups)

        return jsonify({
            "message": f"Escalações da temporada {season} coletadas",
            "matches_with_lineups": len(lineups),
            "lineups_processed": processed,
        })
    except Exception as e:
        return jsonify({"error": f"Erro: {str(e)}"}), 500


@data_collection_bp.route("/collect/odds", methods=["POST"])
def collect_odds():
    """Coleta odds pré-jogo para partidas futuras."""
    data = request.get_json() or {}
    season = data.get("season", 2026)

    if not current_app.config.get("API_FOOTBALL_KEY"):
        return jsonify({"error": "API_FOOTBALL_KEY não configurada"}), 400

    try:
        api = APIFootballService()
        processor = DataProcessor()

        print(f"Coletando odds da temporada {season}...")
        odds_data = api.collect_odds_for_upcoming(season)
        processed = processor.process_odds(odds_data)

        return jsonify({
            "message": f"Odds coletadas com sucesso",
            "fixtures_with_odds": len(odds_data),
            "odds_processed": processed,
        })
    except Exception as e:
        return jsonify({"error": f"Erro: {str(e)}"}), 500


@data_collection_bp.route("/collect/injuries", methods=["POST"])
def collect_injuries():
    """Coleta lesões/suspensões para partidas futuras."""
    data = request.get_json() or {}
    season = data.get("season", 2026)

    if not current_app.config.get("API_FOOTBALL_KEY"):
        return jsonify({"error": "API_FOOTBALL_KEY não configurada"}), 400

    try:
        api = APIFootballService()
        processor = DataProcessor()

        print(f"Coletando lesões da temporada {season}...")
        injuries_data = api.collect_injuries_upcoming(season)
        processed = processor.process_injuries(injuries_data)

        return jsonify({
            "message": f"Lesões coletadas com sucesso",
            "fixtures_with_injuries": len(injuries_data),
            "injuries_processed": processed,
        })
    except Exception as e:
        return jsonify({"error": f"Erro: {str(e)}"}), 500
