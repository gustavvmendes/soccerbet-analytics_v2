import numpy as np
import pandas as pd
from datetime import datetime
from app import db
from app.models.database import Match, MatchStatistics, Team, Season, League


class FeatureEngineering:
    """Gera features para os modelos de ML.

    Separa forma como mandante e visitante e aplica decaimento temporal.
    """

    def __init__(self, n_last_matches=5, decay_lambda=0.005):
        self.n_last = n_last_matches
        self.decay_lambda = decay_lambda

    # ── Dataset para treino ───────────────────────────────
    def build_dataset(self, seasons=None):
        """Constrói dataset com features e targets para treino."""
        query = (
            db.session.query(Match)
            .join(MatchStatistics, Match.id == MatchStatistics.match_id)
            .filter(Match.status == "FT")
            .order_by(Match.date)
        )

        if seasons:
            query = query.join(Season).filter(Season.year.in_(seasons))

        matches = query.all()

        if len(matches) < self.n_last + 1:
            return pd.DataFrame()

        rows = []
        for i, match in enumerate(matches):
            if i < self.n_last * 2:
                continue

            home_id = match.home_team_id
            away_id = match.away_team_id
            match_date = match.date

            # Últimas N como MANDANTE do time da casa
            home_as_home = self._get_previous(matches[:i], home_id, is_home=True)
            # Últimas N geral do time da casa
            home_all = self._get_previous(matches[:i], home_id, is_home=None)
            # Últimas N como VISITANTE do time de fora
            away_as_away = self._get_previous(matches[:i], away_id, is_home=False)
            # Últimas N geral do time de fora
            away_all = self._get_previous(matches[:i], away_id, is_home=None)

            if len(home_all) < self.n_last or len(away_all) < self.n_last:
                continue

            features = {}

            # Features do time da casa (como mandante)
            if len(home_as_home) >= 3:
                h_home_stats = self._aggregate(home_as_home, home_id, match_date)
                for k, v in h_home_stats.items():
                    features[f"home_as_home_{k}"] = v
            else:
                h_all_stats = self._aggregate(home_all, home_id, match_date)
                for k, v in h_all_stats.items():
                    features[f"home_as_home_{k}"] = v

            # Features gerais do time da casa
            h_stats = self._aggregate(home_all, home_id, match_date)
            for k, v in h_stats.items():
                features[f"home_{k}"] = v

            # Features do time de fora (como visitante)
            if len(away_as_away) >= 3:
                a_away_stats = self._aggregate(away_as_away, away_id, match_date)
                for k, v in a_away_stats.items():
                    features[f"away_as_away_{k}"] = v
            else:
                a_all_stats = self._aggregate(away_all, away_id, match_date)
                for k, v in a_all_stats.items():
                    features[f"away_as_away_{k}"] = v

            # Features gerais do time de fora
            a_stats = self._aggregate(away_all, away_id, match_date)
            for k, v in a_stats.items():
                features[f"away_{k}"] = v

            # H2H
            h2h = self._get_h2h(matches[:i], home_id, away_id)
            features.update(self._aggregate_h2h(h2h, home_id))

            # Targets
            targets = self._compute_targets(match)

            row = {**features, **targets}
            row["match_id"] = match.id
            row["date"] = match.date

            # Peso temporal (para sample_weight no XGBoost)
            days_ago = (datetime.utcnow() - match.date).days
            row["sample_weight"] = np.exp(-self.decay_lambda * days_ago)

            rows.append(row)

        return pd.DataFrame(rows)

    # ── Features para predição ────────────────────────────
    def compute_prediction_features(self, home_team_api_id, away_team_api_id):
        """Calcula features para uma partida futura."""
        home_team = Team.query.filter_by(api_id=home_team_api_id).first()
        away_team = Team.query.filter_by(api_id=away_team_api_id).first()

        if not home_team or not away_team:
            return None

        all_matches = (
            db.session.query(Match)
            .join(MatchStatistics)
            .filter(Match.status == "FT")
            .order_by(Match.date)
            .all()
        )

        now = datetime.utcnow()
        home_id = home_team.id
        away_id = away_team.id

        home_as_home = self._get_previous(all_matches, home_id, is_home=True)
        home_all = self._get_previous(all_matches, home_id, is_home=None)
        away_as_away = self._get_previous(all_matches, away_id, is_home=False)
        away_all = self._get_previous(all_matches, away_id, is_home=None)

        if len(home_all) < self.n_last or len(away_all) < self.n_last:
            return None

        features = {}

        src = home_as_home if len(home_as_home) >= 3 else home_all
        for k, v in self._aggregate(src, home_id, now).items():
            features[f"home_as_home_{k}"] = v
        for k, v in self._aggregate(home_all, home_id, now).items():
            features[f"home_{k}"] = v

        src = away_as_away if len(away_as_away) >= 3 else away_all
        for k, v in self._aggregate(src, away_id, now).items():
            features[f"away_as_away_{k}"] = v
        for k, v in self._aggregate(away_all, away_id, now).items():
            features[f"away_{k}"] = v

        h2h = self._get_h2h(all_matches, home_id, away_id)
        features.update(self._aggregate_h2h(h2h, home_id))

        return features

    # ── Helpers privados ──────────────────────────────────
    def _get_previous(self, matches, team_id, is_home=None):
        filtered = []
        for m in matches:
            if is_home is True and m.home_team_id == team_id:
                filtered.append(m)
            elif is_home is False and m.away_team_id == team_id:
                filtered.append(m)
            elif is_home is None and (m.home_team_id == team_id or m.away_team_id == team_id):
                filtered.append(m)
        return filtered[-self.n_last:]

    def _get_h2h(self, matches, team1_id, team2_id):
        h2h = [
            m for m in matches
            if (m.home_team_id == team1_id and m.away_team_id == team2_id)
            or (m.home_team_id == team2_id and m.away_team_id == team1_id)
        ]
        return h2h[-10:]

    def _aggregate(self, matches, team_id, ref_date):
        """Agrega estatísticas com decaimento temporal."""
        goals_scored, goals_conceded = [], []
        shots, shots_on_target, corners, cards, possession = [], [], [], [], []
        weights = []
        wins = draws = losses = clean_sheets = 0

        for m in matches:
            is_home = m.home_team_id == team_id
            stats = m.statistics

            if isinstance(ref_date, datetime):
                days = (ref_date - m.date).days
            else:
                days = 0
            w = np.exp(-self.decay_lambda * max(days, 0))
            weights.append(w)

            gs = (m.home_goals if is_home else m.away_goals) or 0
            gc = (m.away_goals if is_home else m.home_goals) or 0
            goals_scored.append(gs)
            goals_conceded.append(gc)

            if gs > gc:
                wins += w
            elif gs == gc:
                draws += w
            else:
                losses += w

            if gc == 0:
                clean_sheets += w

            if stats:
                if is_home:
                    shots.append(stats.home_shots_total or 0)
                    shots_on_target.append(stats.home_shots_on_target or 0)
                    corners.append(stats.home_corners or 0)
                    cards.append((stats.home_yellow_cards or 0) + (stats.home_red_cards or 0))
                    possession.append(stats.home_possession or 50)
                else:
                    shots.append(stats.away_shots_total or 0)
                    shots_on_target.append(stats.away_shots_on_target or 0)
                    corners.append(stats.away_corners or 0)
                    cards.append((stats.away_yellow_cards or 0) + (stats.away_red_cards or 0))
                    possession.append(stats.away_possession or 50)

        total_w = sum(weights) if weights else 1

        def wmean(values, w_list):
            if not values:
                return 0
            return np.average(values, weights=w_list[: len(values)])

        return {
            "avg_goals_scored": wmean(goals_scored, weights),
            "avg_goals_conceded": wmean(goals_conceded, weights),
            "avg_shots": wmean(shots, weights),
            "avg_shots_on_target": wmean(shots_on_target, weights),
            "avg_corners": wmean(corners, weights),
            "avg_cards": wmean(cards, weights),
            "avg_possession": wmean(possession, weights),
            "win_rate": wins / total_w if total_w else 0,
            "draw_rate": draws / total_w if total_w else 0,
            "loss_rate": losses / total_w if total_w else 0,
            "clean_sheet_rate": clean_sheets / total_w if total_w else 0,
            "goals_scored_std": np.std(goals_scored) if len(goals_scored) > 1 else 0,
            "goals_conceded_std": np.std(goals_conceded) if len(goals_conceded) > 1 else 0,
        }

    def _aggregate_h2h(self, h2h_matches, home_team_id):
        if not h2h_matches:
            return {
                "h2h_home_wins": 0,
                "h2h_draws": 0,
                "h2h_away_wins": 0,
                "h2h_avg_total_goals": 0,
                "h2h_matches_count": 0,
            }

        home_wins = draws = away_wins = 0
        total_goals = []

        for m in h2h_matches:
            hg = m.home_goals or 0
            ag = m.away_goals or 0
            total_goals.append(hg + ag)

            if m.home_team_id == home_team_id:
                if hg > ag:
                    home_wins += 1
                elif hg == ag:
                    draws += 1
                else:
                    away_wins += 1
            else:
                if ag > hg:
                    home_wins += 1
                elif hg == ag:
                    draws += 1
                else:
                    away_wins += 1

        return {
            "h2h_home_wins": home_wins,
            "h2h_draws": draws,
            "h2h_away_wins": away_wins,
            "h2h_avg_total_goals": np.mean(total_goals),
            "h2h_matches_count": len(h2h_matches),
        }

    def _compute_targets(self, match):
        hg = match.home_goals or 0
        ag = match.away_goals or 0
        total = hg + ag
        stats = match.statistics

        if hg > ag:
            result = 2
        elif hg == ag:
            result = 1
        else:
            result = 0

        targets = {
            "target_result": result,
            "target_home_goals": hg,
            "target_away_goals": ag,
            "target_total_goals": total,
            "target_btts": 1 if (hg > 0 and ag > 0) else 0,
            "target_over_05": 1 if total > 0.5 else 0,
            "target_over_15": 1 if total > 1.5 else 0,
            "target_over_25": 1 if total > 2.5 else 0,
            "target_over_35": 1 if total > 3.5 else 0,
        }

        if stats:
            targets["target_home_corners"] = stats.home_corners or 0
            targets["target_away_corners"] = stats.away_corners or 0
            targets["target_home_cards"] = (stats.home_yellow_cards or 0) + (stats.home_red_cards or 0)
            targets["target_away_cards"] = (stats.away_yellow_cards or 0) + (stats.away_red_cards or 0)
            targets["target_home_possession"] = stats.home_possession or 50
            targets["target_away_possession"] = stats.away_possession or 50
            targets["target_home_shots"] = stats.home_shots_total or 0
            targets["target_away_shots"] = stats.away_shots_total or 0
        else:
            targets.update({
                "target_home_corners": 0, "target_away_corners": 0,
                "target_home_cards": 0, "target_away_cards": 0,
                "target_home_possession": 50, "target_away_possession": 50,
                "target_home_shots": 0, "target_away_shots": 0,
            })

        return targets
