"""
Serviço de monitoramento ao vivo de partidas.

Implementa cache com thread-lock para evitar chamadas duplicadas à API.
O frontend pode fazer poll a cada poucos segundos, mas a API só é chamada
a cada FETCH_INTERVAL_SECONDS (padrão: 120s ≈ 2 minutos).
"""

import threading
import time
from datetime import datetime

from flask import current_app

from app.ml.live_predictor import LivePredictor
from app.services.api_football import APIFootballService


class LiveMonitor:
    """Monitor singleton para partidas ao vivo do Brasileirão."""

    FETCH_INTERVAL_SECONDS = 120  # 2 minutos

    def __init__(self):
        self._lock = threading.Lock()
        self._last_fetch: float | None = None
        self._cache: dict = {
            "matches": [],
            "last_updated": None,
        }
        self._snapshots: dict[int, list[dict]] = {}  # fixture_id → lista de snapshots
        self._pre_match_predictions: dict[int, dict] = {}  # fixture_id → pre-match pred
        self._predictor = LivePredictor()

    def get_live_data(self, app) -> dict:
        """
        Retorna dados ao vivo. Busca na API apenas se cache expirou.
        Thread-safe: apenas uma thread pode buscar por vez.
        """
        with self._lock:
            now = time.time()
            should_fetch = (
                self._last_fetch is None
                or (now - self._last_fetch) >= self.FETCH_INTERVAL_SECONDS
            )

            if should_fetch:
                with app.app_context():
                    self._fetch_from_api()
                self._last_fetch = now

        return self._cache

    def get_match_analysis(self, fixture_api_id: int, app) -> dict | None:
        """Retorna análise detalhada de uma partida ao vivo específica."""
        data = self.get_live_data(app)
        for match in data.get("matches", []):
            if match["fixture_id"] == fixture_api_id:
                return match
        return None

    def get_snapshots(self, fixture_api_id: int) -> list[dict]:
        """Retorna histórico de snapshots para visualizar tendências."""
        return self._snapshots.get(fixture_api_id, [])

    def set_pre_match_prediction(self, fixture_api_id: int, prediction: dict):
        """Registra predição pré-jogo para comparação ao vivo."""
        self._pre_match_predictions[fixture_api_id] = prediction

    def _fetch_from_api(self):
        """Busca partidas ao vivo da API e calcula análise ao vivo."""
        try:
            api = APIFootballService()

            # 1. Buscar partidas ao vivo do Brasileirão
            live_fixtures = api.get_live_fixtures()

            if not live_fixtures:
                self._cache = {
                    "matches": [],
                    "last_updated": datetime.utcnow().isoformat(),
                    "status": "no_live_matches",
                }
                return

            matches_analysis = []

            for fixture in live_fixtures:
                try:
                    analysis = self._analyze_fixture(api, fixture)
                    if analysis:
                        matches_analysis.append(analysis)
                except Exception as e:
                    print(f"Erro ao analisar fixture {fixture.get('fixture', {}).get('id')}: {e}")
                    continue

            self._cache = {
                "matches": matches_analysis,
                "last_updated": datetime.utcnow().isoformat(),
                "match_count": len(matches_analysis),
            }

        except Exception as e:
            print(f"Erro no LiveMonitor._fetch_from_api: {e}")

    def _analyze_fixture(self, api: APIFootballService, fixture: dict) -> dict | None:
        """Analisa uma partida ao vivo individual."""
        fixture_id = fixture["fixture"]["id"]
        fixture_info = fixture["fixture"]
        teams_info = fixture["teams"]
        goals = fixture["goals"]
        score = fixture.get("score", {})

        elapsed = fixture_info["status"].get("elapsed") or 0
        status_short = fixture_info["status"]["short"]

        home_name = teams_info["home"]["name"]
        away_name = teams_info["away"]["name"]
        home_api_id = teams_info["home"]["id"]
        away_api_id = teams_info["away"]["id"]
        home_goals = goals["home"] or 0
        away_goals = goals["away"] or 0

        # Buscar estatísticas detalhadas
        time.sleep(0.35)  # Rate limit
        stats_raw = api.get_fixture_statistics(fixture_id)
        stats = self._parse_statistics(stats_raw, home_api_id, away_api_id)

        # Buscar eventos (gols, cartões, substituições)
        time.sleep(0.35)
        events_raw = api.get_fixture_events(fixture_id)
        events = self._parse_events(events_raw)

        # Contar cartões vermelhos
        home_reds = sum(
            1 for e in events
            if e["team_id"] == home_api_id and e["type"] == "Card" and e["detail"] == "Red Card"
        )
        away_reds = sum(
            1 for e in events
            if e["team_id"] == away_api_id and e["type"] == "Card" and e["detail"] == "Red Card"
        )

        # Obter ou gerar predição pré-jogo
        pre_match = self._get_pre_match(fixture_id, home_api_id, away_api_id)

        # Calcular probabilidades ao vivo
        live_probs = self._predictor.calculate_live_probabilities(
            pre_match_lambda_home=pre_match.get("lambda_home", 1.3),
            pre_match_lambda_away=pre_match.get("lambda_away", 1.0),
            current_home_goals=home_goals,
            current_away_goals=away_goals,
            elapsed_minutes=elapsed,
            home_red_cards=home_reds,
            away_red_cards=away_reds,
            home_shots_on_target=stats.get("home_shots_on_target", 0),
            away_shots_on_target=stats.get("away_shots_on_target", 0),
            home_shots_total=stats.get("home_shots_total", 0),
            away_shots_total=stats.get("away_shots_total", 0),
            home_possession=stats.get("home_possession", 50),
            away_possession=stats.get("away_possession", 50),
            home_corners=stats.get("home_corners", 0),
            away_corners=stats.get("away_corners", 0),
            home_dangerous_attacks=stats.get("home_dangerous_attacks", 0),
            away_dangerous_attacks=stats.get("away_dangerous_attacks", 0),
        )

        # Salvar snapshot para cálculo de momentum
        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "elapsed": elapsed,
            **stats,
        }
        if fixture_id not in self._snapshots:
            self._snapshots[fixture_id] = []
        self._snapshots[fixture_id].append(snapshot)
        # Manter apenas últimos 50 snapshots
        self._snapshots[fixture_id] = self._snapshots[fixture_id][-50:]

        # Calcular momentum
        momentum = self._predictor.calculate_momentum(self._snapshots[fixture_id])

        # Gerar insights
        insights = self._predictor.generate_live_insights(
            live_probs, pre_match, elapsed,
            home_name, away_name,
            home_goals, away_goals,
            home_reds, away_reds,
            momentum,
        )

        return {
            "fixture_id": fixture_id,
            "status": status_short,
            "elapsed": elapsed,
            "home_team": {
                "api_id": home_api_id,
                "name": home_name,
                "logo": teams_info["home"].get("logo"),
            },
            "away_team": {
                "api_id": away_api_id,
                "name": away_name,
                "logo": teams_info["away"].get("logo"),
            },
            "score": {
                "home": home_goals,
                "away": away_goals,
                "halftime": {
                    "home": score.get("halftime", {}).get("home"),
                    "away": score.get("halftime", {}).get("away"),
                },
            },
            "statistics": stats,
            "events": events,
            "live_probabilities": live_probs,
            "pre_match_probabilities": {
                "home_win": pre_match.get("home_win_prob"),
                "draw": pre_match.get("draw_prob"),
                "away_win": pre_match.get("away_win_prob"),
            },
            "momentum": momentum,
            "insights": insights,
            "snapshot_count": len(self._snapshots.get(fixture_id, [])),
        }

    def _get_pre_match(self, fixture_id, home_api_id, away_api_id) -> dict:
        """Obtém predição pré-jogo do cache ou gera uma nova."""
        if fixture_id in self._pre_match_predictions:
            return self._pre_match_predictions[fixture_id]

        # Tentar gerar usando o Predictor
        try:
            from app.ml.predictor import Predictor
            predictor = Predictor()
            predictor.load()
            pred = predictor.predict(home_api_id, away_api_id, save=False)
            self._pre_match_predictions[fixture_id] = pred
            return pred
        except Exception as e:
            print(f"Não conseguiu gerar predição pré-jogo para fixture {fixture_id}: {e}")
            # Retornar valores padrão
            return {
                "lambda_home": 1.3,
                "lambda_away": 1.0,
                "home_win_prob": 0.40,
                "draw_prob": 0.28,
                "away_win_prob": 0.32,
            }

    @staticmethod
    def _parse_statistics(stats_raw: list, home_api_id: int, away_api_id: int) -> dict:
        """Converte estatísticas brutas da API em dict normalizado."""
        result = {
            "home_possession": 50, "away_possession": 50,
            "home_shots_total": 0, "away_shots_total": 0,
            "home_shots_on_target": 0, "away_shots_on_target": 0,
            "home_corners": 0, "away_corners": 0,
            "home_fouls": 0, "away_fouls": 0,
            "home_offsides": 0, "away_offsides": 0,
            "home_yellow_cards": 0, "away_yellow_cards": 0,
            "home_red_cards": 0, "away_red_cards": 0,
            "home_passes_total": 0, "away_passes_total": 0,
            "home_passes_accurate": 0, "away_passes_accurate": 0,
            "home_dangerous_attacks": 0, "away_dangerous_attacks": 0,
            "home_attacks": 0, "away_attacks": 0,
        }

        stat_map = {
            "Ball Possession": ("possession", lambda v: float(v.replace("%", "")) if v else 50),
            "Total Shots": ("shots_total", lambda v: int(v) if v else 0),
            "Shots on Goal": ("shots_on_target", lambda v: int(v) if v else 0),
            "Corner Kicks": ("corners", lambda v: int(v) if v else 0),
            "Fouls": ("fouls", lambda v: int(v) if v else 0),
            "Offsides": ("offsides", lambda v: int(v) if v else 0),
            "Yellow Cards": ("yellow_cards", lambda v: int(v) if v else 0),
            "Red Cards": ("red_cards", lambda v: int(v) if v else 0),
            "Total passes": ("passes_total", lambda v: int(v) if v else 0),
            "Passes accurate": ("passes_accurate", lambda v: int(v) if v else 0),
            "dangerous_attacks": ("dangerous_attacks", lambda v: int(v) if v else 0),
            "Attacks": ("attacks", lambda v: int(v) if v else 0),
        }

        for team_stats in stats_raw:
            team_id = team_stats.get("team", {}).get("id")
            prefix = "home" if team_id == home_api_id else "away"

            for stat in team_stats.get("statistics", []):
                stat_type = stat.get("type", "")
                stat_value = stat.get("value")

                for api_name, (key, parser) in stat_map.items():
                    if stat_type.lower() == api_name.lower():
                        try:
                            result[f"{prefix}_{key}"] = parser(str(stat_value)) if stat_value is not None else 0
                        except (ValueError, TypeError):
                            pass
                        break

        return result

    @staticmethod
    def _parse_events(events_raw: list) -> list[dict]:
        """Converte eventos brutos da API em lista limpa."""
        events = []
        for event in events_raw:
            events.append({
                "time_elapsed": event.get("time", {}).get("elapsed"),
                "time_extra": event.get("time", {}).get("extra"),
                "team_id": event.get("team", {}).get("id"),
                "team_name": event.get("team", {}).get("name"),
                "player_name": event.get("player", {}).get("name"),
                "assist_name": event.get("assist", {}).get("name"),
                "type": event.get("type"),
                "detail": event.get("detail"),
                "comments": event.get("comments"),
            })
        return sorted(events, key=lambda e: (e.get("time_elapsed") or 0))


# ── Instância singleton ──
_live_monitor: LiveMonitor | None = None
_monitor_lock = threading.Lock()


def get_live_monitor() -> LiveMonitor:
    """Retorna instância singleton do LiveMonitor."""
    global _live_monitor
    if _live_monitor is None:
        with _monitor_lock:
            if _live_monitor is None:
                _live_monitor = LiveMonitor()
    return _live_monitor
