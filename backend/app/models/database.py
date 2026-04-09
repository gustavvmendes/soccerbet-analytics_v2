from app import db
from datetime import datetime
import json


class League(db.Model):
    __tablename__ = "leagues"

    id = db.Column(db.Integer, primary_key=True)
    api_id = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100))
    logo = db.Column(db.String(300))
    seasons = db.relationship("Season", backref="league", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "api_id": self.api_id,
            "name": self.name,
            "country": self.country,
            "logo": self.logo,
        }


class Season(db.Model):
    __tablename__ = "seasons"

    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey("leagues.id"), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    matches = db.relationship("Match", backref="season", lazy=True)

    __table_args__ = (db.UniqueConstraint("league_id", "year"),)


class Team(db.Model):
    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)
    api_id = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    logo = db.Column(db.String(300))
    country = db.Column(db.String(100))

    def to_dict(self):
        return {
            "id": self.id,
            "api_id": self.api_id,
            "name": self.name,
            "logo": self.logo,
            "country": self.country,
        }


class Match(db.Model):
    __tablename__ = "matches"

    id = db.Column(db.Integer, primary_key=True)
    api_id = db.Column(db.Integer, unique=True, nullable=False)
    season_id = db.Column(db.Integer, db.ForeignKey("seasons.id"), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    round = db.Column(db.String(50))
    status = db.Column(db.String(20))

    home_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)

    home_goals = db.Column(db.Integer)
    away_goals = db.Column(db.Integer)
    home_goals_ht = db.Column(db.Integer)
    away_goals_ht = db.Column(db.Integer)

    home_team = db.relationship("Team", foreign_keys=[home_team_id])
    away_team = db.relationship("Team", foreign_keys=[away_team_id])
    statistics = db.relationship("MatchStatistics", backref="match", uselist=False)

    def to_dict(self):
        return {
            "id": self.id,
            "api_id": self.api_id,
            "date": self.date.isoformat() if self.date else None,
            "round": self.round,
            "status": self.status,
            "home_team": self.home_team.to_dict() if self.home_team else None,
            "away_team": self.away_team.to_dict() if self.away_team else None,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "statistics": self.statistics.to_dict() if self.statistics else None,
        }


class MatchStatistics(db.Model):
    __tablename__ = "match_statistics"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), unique=True, nullable=False)

    home_possession = db.Column(db.Float)
    away_possession = db.Column(db.Float)
    home_shots_total = db.Column(db.Integer)
    away_shots_total = db.Column(db.Integer)
    home_shots_on_target = db.Column(db.Integer)
    away_shots_on_target = db.Column(db.Integer)
    home_corners = db.Column(db.Integer)
    away_corners = db.Column(db.Integer)
    home_yellow_cards = db.Column(db.Integer)
    away_yellow_cards = db.Column(db.Integer)
    home_red_cards = db.Column(db.Integer)
    away_red_cards = db.Column(db.Integer)
    home_fouls = db.Column(db.Integer)
    away_fouls = db.Column(db.Integer)
    home_offsides = db.Column(db.Integer)
    away_offsides = db.Column(db.Integer)
    home_passes_total = db.Column(db.Integer)
    away_passes_total = db.Column(db.Integer)
    home_passes_accurate = db.Column(db.Integer)
    away_passes_accurate = db.Column(db.Integer)

    def to_dict(self):
        return {
            "home_possession": self.home_possession,
            "away_possession": self.away_possession,
            "home_shots_total": self.home_shots_total,
            "away_shots_total": self.away_shots_total,
            "home_shots_on_target": self.home_shots_on_target,
            "away_shots_on_target": self.away_shots_on_target,
            "home_corners": self.home_corners,
            "away_corners": self.away_corners,
            "home_yellow_cards": self.home_yellow_cards,
            "away_yellow_cards": self.away_yellow_cards,
            "home_red_cards": self.home_red_cards,
            "away_red_cards": self.away_red_cards,
            "home_fouls": self.home_fouls,
            "away_fouls": self.away_fouls,
        }


class Prediction(db.Model):
    __tablename__ = "predictions"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    home_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    league_id = db.Column(db.Integer, db.ForeignKey("leagues.id"), nullable=False)

    home_team = db.relationship("Team", foreign_keys=[home_team_id])
    away_team = db.relationship("Team", foreign_keys=[away_team_id])
    league = db.relationship("League")

    # Resultado
    home_win_prob = db.Column(db.Float)
    draw_prob = db.Column(db.Float)
    away_win_prob = db.Column(db.Float)

    # Placar previsto (lambda do Poisson)
    predicted_home_goals = db.Column(db.Float)
    predicted_away_goals = db.Column(db.Float)

    # Over/Under
    over_05_prob = db.Column(db.Float)
    over_15_prob = db.Column(db.Float)
    over_25_prob = db.Column(db.Float)
    over_35_prob = db.Column(db.Float)

    # BTTS
    btts_prob = db.Column(db.Float)

    # Estatísticas previstas (XGBoost)
    predicted_home_corners = db.Column(db.Float)
    predicted_away_corners = db.Column(db.Float)
    predicted_home_cards = db.Column(db.Float)
    predicted_away_cards = db.Column(db.Float)
    predicted_home_possession = db.Column(db.Float)
    predicted_away_possession = db.Column(db.Float)
    predicted_home_shots = db.Column(db.Float)
    predicted_away_shots = db.Column(db.Float)

    # Matriz de placares (JSON serializado)
    score_matrix = db.Column(db.Text)

    # Confiança da predição
    confidence = db.Column(db.String(10))  # alta, media, baixa

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "home_team": self.home_team.to_dict() if self.home_team else None,
            "away_team": self.away_team.to_dict() if self.away_team else None,
            "league": self.league.to_dict() if self.league else None,
            "confidence": self.confidence,
            "result": {
                "home_win_prob": self.home_win_prob,
                "draw_prob": self.draw_prob,
                "away_win_prob": self.away_win_prob,
            },
            "score": {
                "predicted_home_goals": self.predicted_home_goals,
                "predicted_away_goals": self.predicted_away_goals,
            },
            "over_under": {
                "over_05": self.over_05_prob,
                "over_15": self.over_15_prob,
                "over_25": self.over_25_prob,
                "over_35": self.over_35_prob,
            },
            "btts": self.btts_prob,
            "statistics": {
                "corners": {"home": self.predicted_home_corners, "away": self.predicted_away_corners},
                "cards": {"home": self.predicted_home_cards, "away": self.predicted_away_cards},
                "possession": {"home": self.predicted_home_possession, "away": self.predicted_away_possession},
                "shots": {"home": self.predicted_home_shots, "away": self.predicted_away_shots},
            },
            "score_matrix": json.loads(self.score_matrix) if self.score_matrix else None,
        }


class Player(db.Model):
    __tablename__ = "players"

    id = db.Column(db.Integer, primary_key=True)
    api_id = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    firstname = db.Column(db.String(50))
    lastname = db.Column(db.String(50))
    age = db.Column(db.Integer)
    nationality = db.Column(db.String(50))
    height = db.Column(db.String(20))
    weight = db.Column(db.String(20))
    photo = db.Column(db.String(300))
    position = db.Column(db.String(30))
    number = db.Column(db.Integer)
    team_api_id = db.Column(db.Integer)

    season_stats = db.relationship("PlayerSeasonStats", backref="player", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "api_id": self.api_id,
            "name": self.name,
            "firstname": self.firstname,
            "lastname": self.lastname,
            "age": self.age,
            "nationality": self.nationality,
            "height": self.height,
            "weight": self.weight,
            "photo": self.photo,
            "position": self.position,
            "number": self.number,
            "team_api_id": self.team_api_id,
        }


class PlayerSeasonStats(db.Model):
    __tablename__ = "player_season_stats"

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)
    player_api_id = db.Column(db.Integer, nullable=False)
    team_api_id = db.Column(db.Integer, nullable=False)
    league_id = db.Column(db.Integer, default=71)
    season = db.Column(db.Integer, nullable=False)

    appearances = db.Column(db.Integer, default=0)
    lineups = db.Column(db.Integer, default=0)
    minutes = db.Column(db.Integer, default=0)
    rating = db.Column(db.Float)
    goals = db.Column(db.Integer, default=0)
    assists = db.Column(db.Integer, default=0)
    yellow_cards = db.Column(db.Integer, default=0)
    red_cards = db.Column(db.Integer, default=0)
    shots_total = db.Column(db.Integer, default=0)
    shots_on = db.Column(db.Integer, default=0)
    passes_total = db.Column(db.Integer, default=0)
    passes_key = db.Column(db.Integer, default=0)
    passes_accuracy = db.Column(db.Float)
    tackles = db.Column(db.Integer, default=0)
    interceptions = db.Column(db.Integer, default=0)
    duels_total = db.Column(db.Integer, default=0)
    duels_won = db.Column(db.Integer, default=0)
    dribbles_attempts = db.Column(db.Integer, default=0)
    dribbles_success = db.Column(db.Integer, default=0)
    fouls_drawn = db.Column(db.Integer, default=0)
    fouls_committed = db.Column(db.Integer, default=0)

    __table_args__ = (db.UniqueConstraint("player_api_id", "team_api_id", "season"),)

    def to_dict(self):
        return {
            "player_api_id": self.player_api_id,
            "team_api_id": self.team_api_id,
            "season": self.season,
            "appearances": self.appearances,
            "lineups": self.lineups,
            "minutes": self.minutes,
            "rating": self.rating,
            "goals": self.goals,
            "assists": self.assists,
            "yellow_cards": self.yellow_cards,
            "red_cards": self.red_cards,
            "shots_total": self.shots_total,
            "shots_on": self.shots_on,
            "passes_total": self.passes_total,
            "passes_key": self.passes_key,
            "passes_accuracy": self.passes_accuracy,
            "tackles": self.tackles,
            "interceptions": self.interceptions,
            "duels_total": self.duels_total,
            "duels_won": self.duels_won,
            "dribbles_attempts": self.dribbles_attempts,
            "dribbles_success": self.dribbles_success,
            "fouls_drawn": self.fouls_drawn,
            "fouls_committed": self.fouls_committed,
        }


class MatchLineup(db.Model):
    __tablename__ = "match_lineups"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=False)
    team_api_id = db.Column(db.Integer, nullable=False)
    formation = db.Column(db.String(20))
    player_api_id = db.Column(db.Integer, nullable=False)
    player_name = db.Column(db.String(100))
    player_number = db.Column(db.Integer)
    player_pos = db.Column(db.String(5))
    player_grid = db.Column(db.String(10))
    is_starter = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            "team_api_id": self.team_api_id,
            "formation": self.formation,
            "player_api_id": self.player_api_id,
            "player_name": self.player_name,
            "player_number": self.player_number,
            "player_pos": self.player_pos,
            "player_grid": self.player_grid,
            "is_starter": self.is_starter,
        }


class MatchInjury(db.Model):
    __tablename__ = "match_injuries"

    id = db.Column(db.Integer, primary_key=True)
    match_api_id = db.Column(db.Integer, nullable=False)
    team_api_id = db.Column(db.Integer, nullable=False)
    player_api_id = db.Column(db.Integer, nullable=False)
    player_name = db.Column(db.String(100))
    player_photo = db.Column(db.String(300))
    injury_type = db.Column(db.String(50))
    reason = db.Column(db.String(100))

    def to_dict(self):
        return {
            "team_api_id": self.team_api_id,
            "player_api_id": self.player_api_id,
            "player_name": self.player_name,
            "player_photo": self.player_photo,
            "type": self.injury_type,
            "reason": self.reason,
        }


class MatchOdds(db.Model):
    __tablename__ = "match_odds"

    id = db.Column(db.Integer, primary_key=True)
    match_api_id = db.Column(db.Integer, unique=True, nullable=False)
    bookmaker = db.Column(db.String(50))
    home_win_odd = db.Column(db.Float)
    draw_odd = db.Column(db.Float)
    away_win_odd = db.Column(db.Float)
    over_25_odd = db.Column(db.Float)
    under_25_odd = db.Column(db.Float)
    btts_yes_odd = db.Column(db.Float)
    btts_no_odd = db.Column(db.Float)
    double_chance_home_draw = db.Column(db.Float)
    double_chance_draw_away = db.Column(db.Float)
    double_chance_home_away = db.Column(db.Float)

    def to_dict(self):
        # Converter odds em probabilidades implícitas
        def odd_to_prob(odd):
            return (1 / odd * 100) if odd and odd > 0 else None

        return {
            "bookmaker": self.bookmaker,
            "match_winner": {
                "home": self.home_win_odd,
                "draw": self.draw_odd,
                "away": self.away_win_odd,
            },
            "match_winner_probs": {
                "home": odd_to_prob(self.home_win_odd),
                "draw": odd_to_prob(self.draw_odd),
                "away": odd_to_prob(self.away_win_odd),
            },
            "over_under_25": {
                "over": self.over_25_odd,
                "under": self.under_25_odd,
            },
            "btts": {
                "yes": self.btts_yes_odd,
                "no": self.btts_no_odd,
            },
            "double_chance": {
                "home_draw": self.double_chance_home_draw,
                "draw_away": self.double_chance_draw_away,
                "home_away": self.double_chance_home_away,
            },
        }
