from app import db
from datetime import datetime


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
        import json

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
