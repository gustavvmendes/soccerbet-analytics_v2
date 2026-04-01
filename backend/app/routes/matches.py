from flask import Blueprint, jsonify, request
from app import db
from app.models.database import Match, Team, Season, League, Prediction

matches_bp = Blueprint("matches", __name__)


@matches_bp.route("/teams", methods=["GET"])
def get_teams():
    teams = Team.query.order_by(Team.name).all()
    return jsonify([t.to_dict() for t in teams])


@matches_bp.route("/history", methods=["GET"])
def get_history():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    per_page = min(per_page, 100)
    team_id = request.args.get("team_id", type=int)
    season_year = request.args.get("season", type=int)

    query = (
        Match.query
        .filter(Match.status == "FT")
        .order_by(Match.date.desc())
    )

    if team_id:
        team = Team.query.filter_by(api_id=team_id).first()
        if team:
            query = query.filter(
                (Match.home_team_id == team.id) | (Match.away_team_id == team.id)
            )

    if season_year:
        query = query.join(Season).filter(Season.year == season_year)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "matches": [m.to_dict() for m in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
    })


@matches_bp.route("/upcoming", methods=["GET"])
def get_upcoming():
    """Retorna próximos jogos agendados."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    per_page = min(per_page, 100)

    query = (
        Match.query
        .filter(Match.status.in_(["NS", "TBD", "PST", "SUSP"]))
        .order_by(Match.date.asc())
    )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "matches": [m.to_dict() for m in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
    })


@matches_bp.route("/h2h", methods=["GET"])
def get_h2h():
    home_api_id = request.args.get("home_team", type=int)
    away_api_id = request.args.get("away_team", type=int)

    if not home_api_id or not away_api_id:
        return jsonify({"error": "home_team e away_team são obrigatórios"}), 400

    home = Team.query.filter_by(api_id=home_api_id).first()
    away = Team.query.filter_by(api_id=away_api_id).first()

    if not home or not away:
        return jsonify({"error": "Time não encontrado"}), 404

    matches = (
        Match.query
        .filter(Match.status == "FT")
        .filter(
            ((Match.home_team_id == home.id) & (Match.away_team_id == away.id))
            | ((Match.home_team_id == away.id) & (Match.away_team_id == home.id))
        )
        .order_by(Match.date.desc())
        .limit(20)
        .all()
    )

    return jsonify({
        "home_team": home.to_dict(),
        "away_team": away.to_dict(),
        "matches": [m.to_dict() for m in matches],
        "total": len(matches),
    })


@matches_bp.route("/stats", methods=["GET"])
def get_stats():
    """Estatísticas gerais do banco de dados."""
    total_matches = Match.query.filter(Match.status == "FT").count()
    total_teams = Team.query.count()
    seasons = db.session.query(Season.year).order_by(Season.year).all()

    return jsonify({
        "total_matches": total_matches,
        "total_teams": total_teams,
        "seasons": [s.year for s in seasons],
    })


@matches_bp.route("/<int:match_id>/details", methods=["GET"])
def get_match_details(match_id):
    """Retorna detalhes da partida (resultado real + predição do modelo)."""
    match = Match.query.get(match_id)
    if not match:
        return jsonify({"error": "Partida não encontrada"}), 404

    match_dict = match.to_dict()

    # Gerar predição retroativa com o modelo atual
    prediction_data = None
    try:
        from app.ml.predictor import Predictor
        predictor = Predictor()
        prediction_data = predictor.predict(
            match.home_team.api_id,
            match.away_team.api_id,
            save=False,
        )
    except Exception:
        pass

    return jsonify({
        "match": match_dict,
        "prediction": prediction_data,
    })
