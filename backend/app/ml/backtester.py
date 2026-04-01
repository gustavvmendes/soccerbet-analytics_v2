import numpy as np
import pandas as pd
from datetime import datetime
from app import db
from app.models.database import Match, MatchStatistics, Season
from app.ml.dixon_coles import DixonColesModel
from app.ml.xgboost_models import XGBoostModels
from app.ml.feature_engineering import FeatureEngineering


class Backtester:
    """Backtesting: simula predições rodada a rodada para avaliar os modelos."""

    def __init__(self, min_train_matches=50):
        self.min_train_matches = min_train_matches

    def run(self, seasons=None):
        """Executa backtesting temporal rodada a rodada."""
        matches = (
            db.session.query(Match)
            .join(MatchStatistics)
            .filter(Match.status == "FT")
            .order_by(Match.date)
        )

        if seasons:
            matches = matches.join(Season).filter(Season.year.in_(seasons))

        matches = matches.all()

        if len(matches) < self.min_train_matches + 10:
            raise ValueError(f"Dados insuficientes ({len(matches)} partidas)")

        results = []

        # Simular: para cada partida após as primeiras N, treinar e prever
        test_start = self.min_train_matches
        step = 10  # Avaliar a cada 10 partidas para não demorar muito

        for i in range(test_start, len(matches), step):
            train_matches = matches[:i]
            test_batch = matches[i: i + step]

            try:
                # Treinar Dixon-Coles com partidas até este ponto
                dc = DixonColesModel()

                # Construir dados temporários para treino
                team_ids = set()
                for m in train_matches:
                    team_ids.add(m.home_team_id)
                    team_ids.add(m.away_team_id)

                dc.teams = sorted(team_ids)
                dc.team_index = {t: idx for idx, t in enumerate(dc.teams)}

                now = train_matches[-1].date
                dc_matches_data = []
                dc_weights = []

                for m in train_matches:
                    if m.home_team_id in dc.team_index and m.away_team_id in dc.team_index:
                        dc_matches_data.append((
                            dc.team_index[m.home_team_id],
                            dc.team_index[m.away_team_id],
                            m.home_goals,
                            m.away_goals,
                        ))
                        days = (now - m.date).days
                        dc_weights.append(np.exp(-dc.decay_lambda * days))

                n_teams = len(dc.teams)
                x0 = np.zeros(2 * n_teams + 2)
                x0[2 * n_teams] = 0.25
                x0[2 * n_teams + 1] = -0.05

                from scipy.optimize import minimize

                constraints = [{"type": "eq", "fun": lambda p, n=n_teams: np.sum(p[:n])}]
                bounds = [(None, None)] * (2 * n_teams + 1) + [(-0.5, 0.5)]

                opt = minimize(
                    dc._log_likelihood, x0,
                    args=(dc_matches_data, dc_weights),
                    method="SLSQP", constraints=constraints, bounds=bounds,
                    options={"maxiter": 300, "ftol": 1e-7},
                )
                dc.params = opt.x

                # Avaliar cada partida de teste
                for m in test_batch:
                    if m.home_team_id not in dc.team_index or m.away_team_id not in dc.team_index:
                        continue

                    pred = dc.predict(m.home_team_id, m.away_team_id)

                    actual_home = m.home_goals
                    actual_away = m.away_goals
                    actual_total = actual_home + actual_away

                    if actual_home > actual_away:
                        actual_result = "home"
                    elif actual_home == actual_away:
                        actual_result = "draw"
                    else:
                        actual_result = "away"

                    # Resultado previsto
                    probs = {
                        "home": pred["home_win_prob"],
                        "draw": pred["draw_prob"],
                        "away": pred["away_win_prob"],
                    }
                    predicted_result = max(probs, key=probs.get)

                    results.append({
                        "match_id": m.id,
                        "date": m.date.isoformat(),
                        "train_size": i,
                        "actual_result": actual_result,
                        "predicted_result": predicted_result,
                        "result_correct": actual_result == predicted_result,
                        "home_win_prob": pred["home_win_prob"],
                        "draw_prob": pred["draw_prob"],
                        "away_win_prob": pred["away_win_prob"],
                        "actual_home_goals": actual_home,
                        "actual_away_goals": actual_away,
                        "predicted_home_goals": pred["lambda_home"],
                        "predicted_away_goals": pred["lambda_away"],
                        "actual_total": actual_total,
                        "actual_btts": 1 if (actual_home > 0 and actual_away > 0) else 0,
                        "btts_prob": pred["btts_prob"],
                        "over_25_prob": pred["over_25"],
                        "actual_over_25": 1 if actual_total > 2.5 else 0,
                        "confidence": pred["confidence"],
                    })

            except Exception as e:
                print(f"  Erro no batch {i}: {e}")
                continue

        return self._compute_metrics(results)

    def _compute_metrics(self, results):
        if not results:
            return {"error": "Sem resultados de backtesting"}

        df = pd.DataFrame(results)

        # Acurácia do resultado
        accuracy = df["result_correct"].mean()

        # Acurácia por confiança
        confidence_accuracy = {}
        for conf in ["alta", "media", "baixa"]:
            subset = df[df["confidence"] == conf]
            if len(subset) > 0:
                confidence_accuracy[conf] = {
                    "accuracy": float(subset["result_correct"].mean()),
                    "count": int(len(subset)),
                }

        # MAE dos gols
        mae_home = float(np.mean(np.abs(df["actual_home_goals"] - df["predicted_home_goals"])))
        mae_away = float(np.mean(np.abs(df["actual_away_goals"] - df["predicted_away_goals"])))

        # BTTS accuracy
        btts_pred = (df["btts_prob"] > 0.5).astype(int)
        btts_accuracy = float((btts_pred == df["actual_btts"]).mean())

        # Over 2.5 accuracy
        over25_pred = (df["over_25_prob"] > 0.5).astype(int)
        over25_accuracy = float((over25_pred == df["actual_over_25"]).mean())

        # Evolução da acurácia ao longo do tempo
        df["cumulative_accuracy"] = df["result_correct"].expanding().mean()
        evolution = df[["date", "train_size", "cumulative_accuracy"]].to_dict("records")

        return {
            "total_predictions": len(df),
            "result_accuracy": float(accuracy),
            "confidence_breakdown": confidence_accuracy,
            "goals_mae": {"home": mae_home, "away": mae_away},
            "btts_accuracy": btts_accuracy,
            "over25_accuracy": over25_accuracy,
            "accuracy_evolution": evolution[-20:],  # Últimos 20 pontos
        }
