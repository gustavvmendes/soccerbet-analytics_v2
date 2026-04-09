from datetime import datetime
from app import db
from app.models.database import (
    League, Season, Team, Match, MatchStatistics,
    Player, PlayerSeasonStats, MatchLineup, MatchInjury, MatchOdds,
)


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

    # ── Novos processadores ──────────────────────────────

    def process_squads_and_stats(self, all_data, season_year):
        """Processa elencos e stats de jogadores coletados."""
        players_processed = 0
        stats_processed = 0

        for team_data in all_data:
            team_api_id = team_data["team_api_id"]

            # Squad: info básica dos jogadores
            for squad_entry in team_data.get("squad", []):
                for player_data in squad_entry.get("players", []):
                    p_api_id = player_data["id"]
                    player = Player.query.filter_by(api_id=p_api_id).first()
                    if not player:
                        player = Player(
                            api_id=p_api_id,
                            name=player_data.get("name", ""),
                            position=player_data.get("position"),
                            number=player_data.get("number"),
                            photo=player_data.get("photo"),
                            team_api_id=team_api_id,
                        )
                        db.session.add(player)
                        db.session.flush()
                        players_processed += 1
                    else:
                        player.team_api_id = team_api_id
                        player.number = player_data.get("number") or player.number
                        player.position = player_data.get("position") or player.position
                        player.photo = player_data.get("photo") or player.photo

            # Player stats da temporada
            for ps_entry in team_data.get("player_stats", []):
                p_info = ps_entry.get("player", {})
                p_api_id = p_info.get("id")
                if not p_api_id:
                    continue

                # Garantir que o player existe
                player = Player.query.filter_by(api_id=p_api_id).first()
                if not player:
                    player = Player(
                        api_id=p_api_id,
                        name=p_info.get("name", ""),
                        firstname=p_info.get("firstname"),
                        lastname=p_info.get("lastname"),
                        age=p_info.get("age"),
                        nationality=p_info.get("nationality"),
                        height=p_info.get("height"),
                        weight=p_info.get("weight"),
                        photo=p_info.get("photo"),
                        team_api_id=team_api_id,
                    )
                    db.session.add(player)
                    db.session.flush()
                else:
                    player.firstname = p_info.get("firstname") or player.firstname
                    player.lastname = p_info.get("lastname") or player.lastname
                    player.age = p_info.get("age") or player.age
                    player.nationality = p_info.get("nationality") or player.nationality
                    player.height = p_info.get("height") or player.height
                    player.weight = p_info.get("weight") or player.weight
                    player.photo = p_info.get("photo") or player.photo

                for stat_block in ps_entry.get("statistics", []):
                    league_info = stat_block.get("league", {})
                    if league_info.get("id") != 71:
                        continue

                    games = stat_block.get("games", {})
                    goals_s = stat_block.get("goals", {})
                    passes_s = stat_block.get("passes", {})
                    shots_s = stat_block.get("shots", {})
                    tackles_s = stat_block.get("tackles", {})
                    duels_s = stat_block.get("duels", {})
                    dribbles_s = stat_block.get("dribbles", {})
                    fouls_s = stat_block.get("fouls", {})
                    cards_s = stat_block.get("cards", {})

                    existing = PlayerSeasonStats.query.filter_by(
                        player_api_id=p_api_id,
                        team_api_id=team_api_id,
                        season=season_year,
                    ).first()

                    if existing:
                        ps = existing
                    else:
                        ps = PlayerSeasonStats(
                            player_id=player.id,
                            player_api_id=p_api_id,
                            team_api_id=team_api_id,
                            season=season_year,
                        )
                        db.session.add(ps)
                        stats_processed += 1

                    ps.appearances = games.get("appearences") or 0
                    ps.lineups = games.get("lineups") or 0
                    ps.minutes = games.get("minutes") or 0
                    ps.rating = float(games["rating"]) if games.get("rating") else None
                    ps.goals = goals_s.get("total") or 0
                    ps.assists = goals_s.get("assists") or 0
                    ps.shots_total = shots_s.get("total") or 0
                    ps.shots_on = shots_s.get("on") or 0
                    ps.passes_total = passes_s.get("total") or 0
                    ps.passes_key = passes_s.get("key") or 0
                    ps.passes_accuracy = float(passes_s["accuracy"]) if passes_s.get("accuracy") else None
                    ps.tackles = tackles_s.get("total") or 0
                    ps.interceptions = tackles_s.get("interceptions") or 0
                    ps.duels_total = duels_s.get("total") or 0
                    ps.duels_won = duels_s.get("won") or 0
                    ps.dribbles_attempts = dribbles_s.get("attempts") or 0
                    ps.dribbles_success = dribbles_s.get("success") or 0
                    ps.fouls_drawn = fouls_s.get("drawn") or 0
                    ps.fouls_committed = fouls_s.get("committed") or 0
                    ps.yellow_cards = cards_s.get("yellow") or 0
                    ps.red_cards = cards_s.get("red") or 0

        db.session.commit()
        return {"players": players_processed, "stats": stats_processed}

    def process_lineups(self, lineups_data):
        """Processa escalações coletadas."""
        processed = 0
        for entry in lineups_data:
            fixture_id = entry["fixture_id"]
            match = Match.query.filter_by(api_id=fixture_id).first()
            if not match:
                continue

            existing = MatchLineup.query.filter_by(match_id=match.id).first()
            if existing:
                continue

            for team_lineup in entry.get("lineups", []):
                team_info = team_lineup.get("team", {})
                team_api_id = team_info.get("id")
                formation = team_lineup.get("formation")

                for player in team_lineup.get("startXI", []):
                    p = player.get("player", {})
                    lineup = MatchLineup(
                        match_id=match.id,
                        team_api_id=team_api_id,
                        formation=formation,
                        player_api_id=p.get("id", 0),
                        player_name=p.get("name", ""),
                        player_number=p.get("number"),
                        player_pos=p.get("pos"),
                        player_grid=p.get("grid"),
                        is_starter=True,
                    )
                    db.session.add(lineup)

                for player in team_lineup.get("substitutes", []):
                    p = player.get("player", {})
                    lineup = MatchLineup(
                        match_id=match.id,
                        team_api_id=team_api_id,
                        formation=formation,
                        player_api_id=p.get("id", 0),
                        player_name=p.get("name", ""),
                        player_number=p.get("number"),
                        player_pos=p.get("pos"),
                        player_grid=None,
                        is_starter=False,
                    )
                    db.session.add(lineup)

                processed += 1

        db.session.commit()
        return processed

    def process_injuries(self, injuries_data):
        """Processa lesões/suspensões coletadas."""
        processed = 0
        for entry in injuries_data:
            fixture_id = entry["fixture_id"]

            existing = MatchInjury.query.filter_by(match_api_id=fixture_id).first()
            if existing:
                continue

            for injury in entry.get("injuries", []):
                p = injury.get("player", {})
                t = injury.get("team", {})
                mi = MatchInjury(
                    match_api_id=fixture_id,
                    team_api_id=t.get("id", 0),
                    player_api_id=p.get("id", 0),
                    player_name=p.get("name", ""),
                    player_photo=p.get("photo"),
                    injury_type=p.get("type", ""),
                    reason=p.get("reason", ""),
                )
                db.session.add(mi)
                processed += 1

        db.session.commit()
        return processed

    def process_odds(self, odds_data):
        """Processa odds pré-jogo coletadas."""
        processed = 0
        for entry in odds_data:
            fixture_id = entry["fixture_id"]

            existing = MatchOdds.query.filter_by(match_api_id=fixture_id).first()
            if existing:
                continue

            for bookmaker_data in entry.get("odds", []):
                bookmakers = bookmaker_data.get("bookmakers", [])
                if not bookmakers:
                    continue

                # Pegar o primeiro bookmaker disponível
                bk = bookmakers[0]
                bk_name = bk.get("name", "Unknown")

                odds_obj = MatchOdds(
                    match_api_id=fixture_id,
                    bookmaker=bk_name,
                )

                for bet in bk.get("bets", []):
                    bet_name = bet.get("name", "")
                    values = bet.get("values", [])

                    if bet_name == "Match Winner":
                        for v in values:
                            val = v.get("value")
                            odd = float(v.get("odd", 0))
                            if val == "Home":
                                odds_obj.home_win_odd = odd
                            elif val == "Draw":
                                odds_obj.draw_odd = odd
                            elif val == "Away":
                                odds_obj.away_win_odd = odd

                    elif bet_name == "Goals Over/Under" or bet_name == "Over/Under":
                        for v in values:
                            val = v.get("value", "")
                            odd = float(v.get("odd", 0))
                            if "Over" in str(val) and "2.5" in str(v.get("handicap", val)):
                                odds_obj.over_25_odd = odd
                            elif "Under" in str(val) and "2.5" in str(v.get("handicap", val)):
                                odds_obj.under_25_odd = odd

                    elif bet_name == "Both Teams Score":
                        for v in values:
                            val = v.get("value")
                            odd = float(v.get("odd", 0))
                            if val == "Yes":
                                odds_obj.btts_yes_odd = odd
                            elif val == "No":
                                odds_obj.btts_no_odd = odd

                    elif bet_name == "Double Chance":
                        for v in values:
                            val = v.get("value", "")
                            odd = float(v.get("odd", 0))
                            if val == "Home/Draw":
                                odds_obj.double_chance_home_draw = odd
                            elif val == "Draw/Away":
                                odds_obj.double_chance_draw_away = odd
                            elif val == "Home/Away":
                                odds_obj.double_chance_home_away = odd

                db.session.add(odds_obj)
                processed += 1
                break  # Apenas o primeiro bookmaker

        db.session.commit()
        return processed
