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
