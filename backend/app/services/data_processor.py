from datetime import datetime
from app import db
from app.models.database import League, Season, Team, Match, MatchStatistics


class DataProcessor:
    """Processa e armazena dados coletados da API-Football no banco."""

    @staticmethod
    def _parse_stat(stats_list, stat_name):
        if not stats_list:
            return None
        for stat in stats_list:
            if stat.get("type") == stat_name:
                value = stat.get("value")
                if value is None:
                    return 0
                if isinstance(value, str) and value.endswith("%"):
                    return float(value.replace("%", ""))
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return 0
        return 0

    @staticmethod
    def ensure_league(api_id, name="Brasileirão Série A", country="Brazil", logo=None):
        league = League.query.filter_by(api_id=api_id).first()
        if not league:
            league = League(api_id=api_id, name=name, country=country, logo=logo)
            db.session.add(league)
            db.session.flush()
        return league

    @staticmethod
    def ensure_team(team_data):
        team = Team.query.filter_by(api_id=team_data["id"]).first()
        if not team:
            team = Team(
                api_id=team_data["id"],
                name=team_data["name"],
                logo=team_data.get("logo"),
                country=team_data.get("country"),
            )
            db.session.add(team)
            db.session.flush()
        return team

    @staticmethod
    def ensure_season(league, year):
        season = Season.query.filter_by(league_id=league.id, year=year).first()
        if not season:
            season = Season(league_id=league.id, year=year)
            db.session.add(season)
            db.session.flush()
        return season

    def process_fixture(self, fixture_data, season):
        fixture_info = fixture_data["fixture"]
        teams_info = fixture_data["teams"]
        goals_info = fixture_data["goals"]
        score_info = fixture_data.get("score", {})

        fixture_api_id = fixture_info["id"]

        existing = Match.query.filter_by(api_id=fixture_api_id).first()
        if existing:
            return existing

        home_team = self.ensure_team(teams_info["home"])
        away_team = self.ensure_team(teams_info["away"])

        date_str = fixture_info["date"]
        if date_str.endswith("Z"):
            date_str = date_str.replace("Z", "+00:00")
        match_date = datetime.fromisoformat(date_str)

        ht_score = score_info.get("halftime", {})

        match = Match(
            api_id=fixture_api_id,
            season_id=season.id,
            date=match_date,
            round=fixture_data.get("league", {}).get("round"),
            status=fixture_info["status"]["short"],
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_goals=goals_info.get("home"),
            away_goals=goals_info.get("away"),
            home_goals_ht=ht_score.get("home"),
            away_goals_ht=ht_score.get("away"),
        )
        db.session.add(match)
        db.session.flush()

        stats_data = fixture_data.get("statistics")
        if stats_data and len(stats_data) >= 2:
            home_stats = stats_data[0].get("statistics", [])
            away_stats = stats_data[1].get("statistics", [])

            match_stats = MatchStatistics(
                match_id=match.id,
                home_possession=self._parse_stat(home_stats, "Ball Possession"),
                away_possession=self._parse_stat(away_stats, "Ball Possession"),
                home_shots_total=self._parse_stat(home_stats, "Total Shots"),
                away_shots_total=self._parse_stat(away_stats, "Total Shots"),
                home_shots_on_target=self._parse_stat(home_stats, "Shots on Goal"),
                away_shots_on_target=self._parse_stat(away_stats, "Shots on Goal"),
                home_corners=self._parse_stat(home_stats, "Corner Kicks"),
                away_corners=self._parse_stat(away_stats, "Corner Kicks"),
                home_yellow_cards=self._parse_stat(home_stats, "Yellow Cards"),
                away_yellow_cards=self._parse_stat(away_stats, "Yellow Cards"),
                home_red_cards=self._parse_stat(home_stats, "Red Cards"),
                away_red_cards=self._parse_stat(away_stats, "Red Cards"),
                home_fouls=self._parse_stat(home_stats, "Fouls"),
                away_fouls=self._parse_stat(away_stats, "Fouls"),
                home_offsides=self._parse_stat(home_stats, "Offsides"),
                away_offsides=self._parse_stat(away_stats, "Offsides"),
                home_passes_total=self._parse_stat(home_stats, "Total passes"),
                away_passes_total=self._parse_stat(away_stats, "Total passes"),
                home_passes_accurate=self._parse_stat(home_stats, "Passes accurate"),
                away_passes_accurate=self._parse_stat(away_stats, "Passes accurate"),
            )
            db.session.add(match_stats)

        return match

    def process_season_data(self, fixtures_data, league_api_id, season_year):
        league = self.ensure_league(league_api_id)
        season = self.ensure_season(league, season_year)

        processed = 0
        for fixture_data in fixtures_data:
            try:
                self.process_fixture(fixture_data, season)
                processed += 1
            except Exception as e:
                print(f"Erro ao processar fixture: {e}")
                continue

        db.session.commit()
        return processed

    def process_upcoming_fixtures(self, fixtures_data, league_api_id, season_year):
        """Processa jogos futuros (sem estatísticas, apenas agenda)."""
        league = self.ensure_league(league_api_id)
        season = self.ensure_season(league, season_year)

        processed = 0
        for fixture_data in fixtures_data:
            try:
                fixture_info = fixture_data["fixture"]
                teams_info = fixture_data["teams"]
                fixture_api_id = fixture_info["id"]

                existing = Match.query.filter_by(api_id=fixture_api_id).first()
                if existing:
                    continue

                home_team = self.ensure_team(teams_info["home"])
                away_team = self.ensure_team(teams_info["away"])

                date_str = fixture_info["date"]
                if date_str.endswith("Z"):
                    date_str = date_str.replace("Z", "+00:00")
                match_date = datetime.fromisoformat(date_str)

                match = Match(
                    api_id=fixture_api_id,
                    season_id=season.id,
                    date=match_date,
                    round=fixture_data.get("league", {}).get("round"),
                    status=fixture_info["status"]["short"],
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                )
                db.session.add(match)
                processed += 1
            except Exception as e:
                print(f"Erro ao processar fixture futuro: {e}")
                continue

        db.session.commit()
        return processed
