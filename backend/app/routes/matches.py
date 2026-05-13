from flask import Blueprint, jsonify, request
from app import db
from app.models.database import (
    Match, Team, Season, League, Prediction,
    MatchLineup, MatchInjury, MatchOdds, Player, PlayerSeasonStats,
)

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
    from datetime import datetime

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    per_page = min(per_page, 100)
    team_id = request.args.get("team_id", type=int)
    include_postponed = request.args.get("include_postponed", "false").lower() == "true"

    if include_postponed:
        # Mostrar todos: NS, TBD, PST, SUSP
        query = (
            Match.query
            .filter(Match.status.in_(["NS", "TBD", "PST", "SUSP"]))
            .order_by(Match.date.asc())
        )
    else:
        # Filtrar: NS/TBD normais + PST/SUSP apenas se no futuro
        now = datetime.utcnow()
        query = (
            Match.query
            .filter(
                (Match.status.in_(["NS", "TBD"]))
                | (
                    Match.status.in_(["PST", "SUSP"])
                    & (Match.date >= now)
                )
            )
            .order_by(Match.date.asc())
        )

    if team_id:
        team = Team.query.filter_by(api_id=team_id).first()
        if team:
            query = query.filter(
                (Match.home_team_id == team.id) | (Match.away_team_id == team.id)
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


@matches_bp.route("/<int:match_id>/lineups", methods=["GET"])
def get_match_lineups(match_id):
    """Retorna escalações de uma partida."""
    match = Match.query.get(match_id)
    if not match:
        return jsonify({"error": "Partida não encontrada"}), 404

    lineups = MatchLineup.query.filter_by(match_id=match.id).all()

    # Organizar por time
    teams = {}
    for ln in lineups:
        t_id = ln.team_api_id
        if t_id not in teams:
            team = Team.query.filter_by(api_id=t_id).first()
            teams[t_id] = {
                "team": team.to_dict() if team else {"api_id": t_id},
                "formation": ln.formation,
                "starters": [],
                "substitutes": [],
            }
        entry = ln.to_dict()
        if ln.is_starter:
            teams[t_id]["starters"].append(entry)
        else:
            teams[t_id]["substitutes"].append(entry)

    return jsonify(list(teams.values()))


@matches_bp.route("/<int:match_id>/injuries", methods=["GET"])
def get_match_injuries(match_id):
    """Retorna lesões/suspensões para uma partida."""
    match = Match.query.get(match_id)
    if not match:
        return jsonify({"error": "Partida não encontrada"}), 404

    injuries = MatchInjury.query.filter_by(match_api_id=match.api_id).all()

    # Organizar por time
    by_team = {}
    for inj in injuries:
        t_id = inj.team_api_id
        if t_id not in by_team:
            team = Team.query.filter_by(api_id=t_id).first()
            by_team[t_id] = {
                "team": team.to_dict() if team else {"api_id": t_id},
                "injuries": [],
            }
        by_team[t_id]["injuries"].append(inj.to_dict())

    return jsonify(list(by_team.values()))


@matches_bp.route("/<int:match_id>/odds", methods=["GET"])
def get_match_odds(match_id):
    """Retorna odds pré-jogo de uma partida."""
    match = Match.query.get(match_id)
    if not match:
        return jsonify({"error": "Partida não encontrada"}), 404

    odds = MatchOdds.query.filter_by(match_api_id=match.api_id).first()
    if not odds:
        return jsonify(None)

    return jsonify(odds.to_dict())


@matches_bp.route("/<int:match_id>/explanation", methods=["GET"])
def get_match_explanation(match_id):
    """Retorna explicação detalhada da predição."""
    match = Match.query.get(match_id)
    if not match:
        return jsonify({"error": "Partida não encontrada"}), 404

    try:
        from app.ml.predictor import Predictor
        predictor = Predictor()
        explanation = predictor.get_explanation(
            match.home_team.api_id,
            match.away_team.api_id,
        )
        return jsonify(explanation)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@matches_bp.route("/squad/<int:team_api_id>", methods=["GET"])
def get_squad(team_api_id):
    """Retorna elenco + stats de um time."""
    season = request.args.get("season", 2026, type=int)

    team = Team.query.filter_by(api_id=team_api_id).first()
    if not team:
        return jsonify({"error": "Time não encontrado"}), 404

    players = Player.query.filter_by(team_api_id=team_api_id).all()

    result = []
    for p in players:
        p_dict = p.to_dict()
        stats = PlayerSeasonStats.query.filter_by(
            player_api_id=p.api_id,
            team_api_id=team_api_id,
            season=season,
        ).first()
        p_dict["season_stats"] = stats.to_dict() if stats else None
        result.append(p_dict)

    # Ordenar: por posição (G, D, M, A) e depois por lineups desc
    pos_order = {"Goalkeeper": 0, "Defender": 1, "Midfielder": 2, "Attacker": 3}
    result.sort(key=lambda p: (
        pos_order.get(p.get("position", ""), 4),
        -(p.get("season_stats", {}) or {}).get("lineups", 0),
    ))

    return jsonify({
        "team": team.to_dict(),
        "players": result,
        "season": season,
    })


@matches_bp.route("/<int:match_id>/player-prediction/<int:player_api_id>", methods=["GET"])
def get_player_match_prediction(match_id, player_api_id):
    """Retorna predição individual de um jogador para uma partida."""
    match = Match.query.get(match_id)
    if not match:
        return jsonify({"error": "Partida não encontrada"}), 404

    try:
        from app.ml.predictor import Predictor
        predictor = Predictor()
        result = predictor.predict_player_match(
            player_api_id,
            match.home_team.api_id,
            match.away_team.api_id,
        )
        result["match"] = match.to_dict()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
