import requests
import time
from flask import current_app


class APIFootballService:
    """Serviço para comunicação com a API-Football (v3)."""

    def __init__(self):
        self.base_url = current_app.config["API_FOOTBALL_BASE_URL"]
        self.headers = {
            "x-apisports-key": current_app.config["API_FOOTBALL_KEY"],
        }
        self.league_id = current_app.config["BRASILEIRAO_LEAGUE_ID"]

    def _request(self, endpoint, params=None):
        url = f"{self.base_url}/{endpoint}"
        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("errors") and len(data["errors"]) > 0:
            raise Exception(f"API-Football error: {data['errors']}")

        return data.get("response", [])

    def _paginated_request(self, endpoint, params):
        """Makes paginated requests and returns all results."""
        all_results = []
        page = 1
        while True:
            params["page"] = page
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("errors") and len(data["errors"]) > 0:
                raise Exception(f"API-Football error: {data['errors']}")

            results = data.get("response", [])
            if not results:
                break
            all_results.extend(results)

            paging = data.get("paging", {})
            if page >= paging.get("total", 1):
                break
            page += 1
            time.sleep(0.35)

        return all_results

    def get_leagues(self, country=None):
        params = {}
        if country:
            params["country"] = country
        return self._request("leagues", params)

    def get_teams(self, season):
        return self._request("teams", {"league": self.league_id, "season": season})

    def get_fixtures(self, season, from_date=None, to_date=None):
        params = {"league": self.league_id, "season": season}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        return self._request("fixtures", params)

    def get_fixture_by_id(self, fixture_id):
        result = self._request("fixtures", {"id": fixture_id})
        return result[0] if result else None

    def get_fixture_statistics(self, fixture_id):
        return self._request("fixtures/statistics", {"fixture": fixture_id})

    def get_h2h(self, team1_api_id, team2_api_id, last=20):
        return self._request(
            "fixtures/headtohead",
            {"h2h": f"{team1_api_id}-{team2_api_id}", "last": last},
        )

    def get_standings(self, season):
        return self._request("standings", {"league": self.league_id, "season": season})

    def collect_season_data(self, season):
        """Coleta todas as partidas finalizadas e suas estatísticas."""
        fixtures = self.get_fixtures(season)

        collected = []
        finished = [f for f in fixtures if f["fixture"]["status"]["short"] == "FT"]

        for i, fixture in enumerate(finished):
            fixture_id = fixture["fixture"]["id"]
            try:
                stats = self.get_fixture_statistics(fixture_id)
                fixture["statistics"] = stats
                collected.append(fixture)
                # Respeitar rate limit
                time.sleep(0.35)
                if (i + 1) % 50 == 0:
                    print(f"  Coletadas {i + 1}/{len(finished)} partidas...")
            except Exception as e:
                print(f"Erro ao coletar stats do fixture {fixture_id}: {e}")
                continue

        return collected

    def collect_upcoming_fixtures(self, season):
        """Coleta jogos futuros (ainda não realizados) de uma temporada."""
        fixtures = self.get_fixtures(season)
        upcoming_statuses = {"NS", "TBD", "PST", "SUSP"}
        upcoming = [f for f in fixtures if f["fixture"]["status"]["short"] in upcoming_statuses]
        return upcoming

    # ── Novos endpoints ────────────────────────────────────

    def get_squad(self, team_api_id):
        """Retorna o elenco atual de um time."""
        return self._request("players/squads", {"team": team_api_id})

    def get_player_stats(self, team_api_id, season):
        """Retorna estatísticas dos jogadores de um time na temporada (paginado)."""
        return self._paginated_request("players", {
            "team": team_api_id,
            "season": season,
            "league": self.league_id,
        })

    def get_fixture_lineups(self, fixture_id):
        """Retorna escalações de uma partida."""
        return self._request("fixtures/lineups", {"fixture": fixture_id})

    def get_fixture_events(self, fixture_id):
        """Retorna eventos de uma partida (gols, cartões, substituições)."""
        return self._request("fixtures/events", {"fixture": fixture_id})

    def get_injuries(self, fixture_id=None, league=None, season=None):
        """Retorna lesões/suspensões. Pode filtrar por fixture ou league+season."""
        params = {}
        if fixture_id:
            params["fixture"] = fixture_id
        elif league and season:
            params["league"] = league
            params["season"] = season
        return self._request("injuries", params)

    def get_odds(self, fixture_id):
        """Retorna odds pré-jogo para uma partida."""
        return self._request("odds", {"fixture": fixture_id})

    def collect_all_squads(self, season):
        """Coleta elencos e stats de jogadores de todos os times da temporada."""
        teams = self.get_teams(season)
        all_data = []
        for i, team_entry in enumerate(teams):
            team_api_id = team_entry["team"]["id"]
            team_name = team_entry["team"]["name"]
            try:
                # Elenco atual
                squad = self.get_squad(team_api_id)
                time.sleep(0.35)

                # Stats dos jogadores na temporada
                player_stats = self.get_player_stats(team_api_id, season)
                time.sleep(0.35)

                all_data.append({
                    "team_api_id": team_api_id,
                    "team_name": team_name,
                    "squad": squad,
                    "player_stats": player_stats,
                })

                if (i + 1) % 5 == 0:
                    print(f"  Coletados {i + 1}/{len(teams)} elencos...")
            except Exception as e:
                print(f"Erro ao coletar elenco de {team_name}: {e}")
                continue

        return all_data

    def collect_lineups_for_matches(self, season):
        """Coleta escalações de partidas finalizadas."""
        fixtures = self.get_fixtures(season)
        finished = [f for f in fixtures if f["fixture"]["status"]["short"] == "FT"]
        collected = []

        for i, fixture in enumerate(finished):
            fixture_id = fixture["fixture"]["id"]
            try:
                lineups = self.get_fixture_lineups(fixture_id)
                if lineups:
                    collected.append({
                        "fixture_id": fixture_id,
                        "lineups": lineups,
                    })
                time.sleep(0.35)
                if (i + 1) % 50 == 0:
                    print(f"  Coletadas escalações de {i + 1}/{len(finished)} partidas...")
            except Exception as e:
                print(f"Erro ao coletar lineups do fixture {fixture_id}: {e}")
                continue

        return collected

    def collect_odds_for_upcoming(self, season):
        """Coleta odds pré-jogo para partidas futuras."""
        fixtures = self.get_fixtures(season)
        upcoming_statuses = {"NS", "TBD"}
        upcoming = [f for f in fixtures if f["fixture"]["status"]["short"] in upcoming_statuses]
        collected = []

        for i, fixture in enumerate(upcoming):
            fixture_id = fixture["fixture"]["id"]
            try:
                odds = self.get_odds(fixture_id)
                if odds:
                    collected.append({
                        "fixture_id": fixture_id,
                        "odds": odds,
                    })
                time.sleep(0.35)
                if (i + 1) % 20 == 0:
                    print(f"  Coletadas odds de {i + 1}/{len(upcoming)} partidas...")
            except Exception as e:
                print(f"Erro ao coletar odds do fixture {fixture_id}: {e}")
                continue

        return collected

    def collect_injuries_upcoming(self, season):
        """Coleta lesões/suspensões para partidas futuras."""
        fixtures = self.get_fixtures(season)
        upcoming_statuses = {"NS", "TBD"}
        upcoming = [f for f in fixtures if f["fixture"]["status"]["short"] in upcoming_statuses]
        collected = []

        for i, fixture in enumerate(upcoming):
            fixture_id = fixture["fixture"]["id"]
            try:
                injuries = self.get_injuries(fixture_id=fixture_id)
                if injuries:
                    collected.append({
                        "fixture_id": fixture_id,
                        "injuries": injuries,
                    })
                time.sleep(0.35)
                if (i + 1) % 20 == 0:
                    print(f"  Coletadas lesões de {i + 1}/{len(upcoming)} partidas...")
            except Exception as e:
                print(f"Erro ao coletar injuries do fixture {fixture_id}: {e}")
                continue

        return collected
