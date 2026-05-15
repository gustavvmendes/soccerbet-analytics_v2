import numpy as np
import pandas as pd
from collections import defaultdict
from datetime import datetime
from app import db
from app.models.database import Match, MatchStatistics, Season
from app.ml.dixon_coles import DixonColesModel


class Backtester:
    """Backtesting comparativo: avalia o modelo Dixon-Coles contra duas baselines
    (heurística "sempre casa" e ELO simples) nos mesmos jogos de teste.

    Treina/atualiza walk-forward (sem leakage temporal): para cada batch de teste,
    todos os três modelos só conhecem partidas anteriores ao batch.
    """

    ELO_K = 20
    ELO_HFA = 100  # vantagem de mando em pontos de ELO
    ELO_START = 1500

    def __init__(self, min_train_matches=50):
        self.min_train_matches = min_train_matches

    def run(self, seasons=None):
        query = (
            db.session.query(Match)
            .join(MatchStatistics)
            .filter(Match.status == "FT")
            .order_by(Match.date)
        )

        if seasons:
            query = query.join(Season).filter(Season.year.in_(seasons))

        matches = query.all()

        if len(matches) < self.min_train_matches + 10:
            raise ValueError(f"Dados insuficientes ({len(matches)} partidas)")

        results_dc = []
        results_home = []
        results_elo = []

        test_start = self.min_train_matches
        step = 10
        total_batches = max(1, (len(matches) - test_start) // step)

        for batch_idx, i in enumerate(range(test_start, len(matches), step), start=1):
            train_matches = matches[:i]
            test_batch = matches[i: i + step]
            print(f"  [batch {batch_idx}/{total_batches}] treino={i} jogos, avaliando {len(test_batch)}...", flush=True)

            # ─── Treinar Dixon-Coles com tudo até este ponto ───
            dc = self._train_dc(train_matches)

            # ─── Estatísticas para baseline "sempre casa" ───
            home_rate, draw_rate, away_rate, avg_home_goals, avg_away_goals = self._home_baseline_stats(train_matches)

            # ─── ELO walk-forward a partir do zero até este ponto ───
            elo = self._compute_elo(train_matches)

            # ─── Avaliar cada partida do batch nos três modelos ───
            for m in test_batch:
                actual_home = m.home_goals
                actual_away = m.away_goals
                actual_total = actual_home + actual_away

                if actual_home > actual_away:
                    actual_result = "home"
                elif actual_home == actual_away:
                    actual_result = "draw"
                else:
                    actual_result = "away"

                actual_btts = 1 if (actual_home > 0 and actual_away > 0) else 0
                actual_over_25 = 1 if actual_total > 2.5 else 0

                # ── Dixon-Coles ──
                if dc is not None and m.home_team_id in dc.team_index and m.away_team_id in dc.team_index:
                    try:
                        pred = dc.predict(m.home_team_id, m.away_team_id)
                        probs = {"home": pred["home_win_prob"], "draw": pred["draw_prob"], "away": pred["away_win_prob"]}
                        results_dc.append(self._make_row(
                            m, i, actual_result, actual_home, actual_away, actual_total,
                            actual_btts, actual_over_25, probs,
                            pred["lambda_home"], pred["lambda_away"],
                            pred["btts_prob"], pred["over_25"], pred["confidence"],
                        ))
                    except Exception:
                        pass

                # ── Baseline "sempre casa" ──
                probs_home_baseline = {"home": home_rate, "draw": draw_rate, "away": away_rate}
                results_home.append(self._make_row(
                    m, i, actual_result, actual_home, actual_away, actual_total,
                    actual_btts, actual_over_25, probs_home_baseline,
                    avg_home_goals, avg_away_goals,
                    None, None, "baseline",
                    forced_prediction="home",
                ))

                # ── ELO simples ──
                probs_elo = self._elo_probabilities(elo, m.home_team_id, m.away_team_id)
                results_elo.append(self._make_row(
                    m, i, actual_result, actual_home, actual_away, actual_total,
                    actual_btts, actual_over_25, probs_elo,
                    avg_home_goals, avg_away_goals,
                    None, None, "elo",
                ))

        # ─── Métricas por modelo ───
        return {
            "dixon_coles": self._compute_metrics(results_dc),
            "always_home": self._compute_metrics(results_home),
            "elo": self._compute_metrics(results_elo),
            "summary_table": self._build_summary_table(results_dc, results_home, results_elo),
        }

    # ─────────────────────────────────────────────────────────────
    # Treinamento Dixon-Coles (extraído do código original)
    # ─────────────────────────────────────────────────────────────
    def _train_dc(self, train_matches):
        try:
            dc = DixonColesModel()

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
            return dc
        except Exception as e:
            print(f"  Erro treinando DC: {e}")
            return None

    # ─────────────────────────────────────────────────────────────
    # Baseline "sempre casa": prevê mandante usando taxas históricas
    # ─────────────────────────────────────────────────────────────
    def _home_baseline_stats(self, train_matches):
        n = len(train_matches)
        if n == 0:
            return 0.47, 0.25, 0.28, 1.5, 1.1

        hw = sum(1 for m in train_matches if m.home_goals > m.away_goals)
        d = sum(1 for m in train_matches if m.home_goals == m.away_goals)
        aw = n - hw - d
        avg_home = sum(m.home_goals for m in train_matches) / n
        avg_away = sum(m.away_goals for m in train_matches) / n
        return hw / n, d / n, aw / n, avg_home, avg_away

    # ─────────────────────────────────────────────────────────────
    # ELO simples — calculado walk-forward a partir do zero
    # ─────────────────────────────────────────────────────────────
    def _compute_elo(self, train_matches):
        elo = defaultdict(lambda: float(self.ELO_START))
        for m in train_matches:
            r_h = elo[m.home_team_id]
            r_a = elo[m.away_team_id]
            exp_h = 1.0 / (1.0 + 10 ** (-(r_h + self.ELO_HFA - r_a) / 400.0))

            if m.home_goals > m.away_goals:
                actual_h = 1.0
            elif m.home_goals == m.away_goals:
                actual_h = 0.5
            else:
                actual_h = 0.0

            elo[m.home_team_id] = r_h + self.ELO_K * (actual_h - exp_h)
            elo[m.away_team_id] = r_a + self.ELO_K * ((1.0 - actual_h) - (1.0 - exp_h))
        return elo

    def _elo_probabilities(self, elo, home_id, away_id):
        """Converte ratings ELO em probabilidades de 1X2.

        Usa expected_home da fórmula clássica e deriva empate empiricamente:
        mais empates quando times estão equilibrados, menos quando há disparidade.
        """
        r_h = elo.get(home_id, float(self.ELO_START))
        r_a = elo.get(away_id, float(self.ELO_START))
        exp_h = 1.0 / (1.0 + 10 ** (-(r_h + self.ELO_HFA - r_a) / 400.0))

        # Empate: alto quando exp_h ≈ 0.5, baixo nos extremos
        p_draw = max(0.10, 0.32 - 0.40 * abs(exp_h - 0.5))
        p_home = max(0.05, exp_h - p_draw / 2.0)
        p_away = max(0.05, (1.0 - exp_h) - p_draw / 2.0)

        s = p_home + p_draw + p_away
        return {"home": p_home / s, "draw": p_draw / s, "away": p_away / s}

    # ─────────────────────────────────────────────────────────────
    # Linha de resultado padronizada (usada pelos três modelos)
    # ─────────────────────────────────────────────────────────────
    def _make_row(self, m, train_size, actual_result, actual_home, actual_away,
                  actual_total, actual_btts, actual_over_25, probs,
                  pred_home_goals, pred_away_goals, btts_prob, over_25_prob,
                  confidence, forced_prediction=None):
        predicted_result = forced_prediction if forced_prediction else max(probs, key=probs.get)
        return {
            "match_id": m.id,
            "date": m.date.isoformat(),
            "train_size": train_size,
            "actual_result": actual_result,
            "predicted_result": predicted_result,
            "result_correct": actual_result == predicted_result,
            "home_win_prob": probs["home"],
            "draw_prob": probs["draw"],
            "away_win_prob": probs["away"],
            "actual_home_goals": actual_home,
            "actual_away_goals": actual_away,
            "predicted_home_goals": pred_home_goals,
            "predicted_away_goals": pred_away_goals,
            "actual_total": actual_total,
            "actual_btts": actual_btts,
            "btts_prob": btts_prob,
            "over_25_prob": over_25_prob,
            "actual_over_25": actual_over_25,
            "confidence": confidence,
        }

    # ─────────────────────────────────────────────────────────────
    # Métricas por modelo
    # ─────────────────────────────────────────────────────────────
    def _compute_metrics(self, results):
        if not results:
            return {"error": "Sem resultados"}

        df = pd.DataFrame(results)
        accuracy = float(df["result_correct"].mean())

        # MAE dos gols
        mae_home = float(np.mean(np.abs(df["actual_home_goals"] - df["predicted_home_goals"])))
        mae_away = float(np.mean(np.abs(df["actual_away_goals"] - df["predicted_away_goals"])))

        # Log loss e Brier para o resultado 1X2
        log_loss, brier = self._probability_scores(df)

        out = {
            "total_predictions": int(len(df)),
            "result_accuracy": accuracy,
            "goals_mae": {"home": mae_home, "away": mae_away, "avg": (mae_home + mae_away) / 2},
            "log_loss": log_loss,
            "brier_score": brier,
        }

        # BTTS / Over 2.5 (só quando o modelo realmente fornece prob)
        if "btts_prob" in df.columns and df["btts_prob"].notna().any():
            btts_df = df.dropna(subset=["btts_prob"])
            btts_pred = (btts_df["btts_prob"] > 0.5).astype(int)
            out["btts_accuracy"] = float((btts_pred == btts_df["actual_btts"]).mean())

        if "over_25_prob" in df.columns and df["over_25_prob"].notna().any():
            o_df = df.dropna(subset=["over_25_prob"])
            o_pred = (o_df["over_25_prob"] > 0.5).astype(int)
            out["over25_accuracy"] = float((o_pred == o_df["actual_over_25"]).mean())

        # Breakdown por confiança (só faz sentido para DC)
        conf_breakdown = {}
        for conf in ["alta", "media", "baixa"]:
            subset = df[df["confidence"] == conf]
            if len(subset) > 0:
                conf_breakdown[conf] = {
                    "accuracy": float(subset["result_correct"].mean()),
                    "count": int(len(subset)),
                }
        if conf_breakdown:
            out["confidence_breakdown"] = conf_breakdown

        return out

    def _probability_scores(self, df):
        """Calcula log loss e Brier score multiclasse para o resultado 1X2."""
        eps = 1e-15
        log_losses = []
        briers = []
        for _, row in df.iterrows():
            # one-hot do real
            y_home = 1 if row["actual_result"] == "home" else 0
            y_draw = 1 if row["actual_result"] == "draw" else 0
            y_away = 1 if row["actual_result"] == "away" else 0

            p_home = max(eps, min(1 - eps, row["home_win_prob"]))
            p_draw = max(eps, min(1 - eps, row["draw_prob"]))
            p_away = max(eps, min(1 - eps, row["away_win_prob"]))

            # log loss: -log da prob atribuída ao resultado real
            if y_home:
                log_losses.append(-np.log(p_home))
            elif y_draw:
                log_losses.append(-np.log(p_draw))
            else:
                log_losses.append(-np.log(p_away))

            # Brier multiclasse: soma dos quadrados das diferenças
            briers.append(
                (p_home - y_home) ** 2 + (p_draw - y_draw) ** 2 + (p_away - y_away) ** 2
            )

        return float(np.mean(log_losses)), float(np.mean(briers))

    # ─────────────────────────────────────────────────────────────
    # Tabela-resumo pronta para colar no TCC
    # ─────────────────────────────────────────────────────────────
    def _build_summary_table(self, results_dc, results_home, results_elo):
        models = [
            ("Sempre Casa (baseline trivial)", results_home),
            ("ELO simples", results_elo),
            ("Dixon-Coles + XGBoost", results_dc),
        ]
        rows = []
        for name, results in models:
            if not results:
                continue
            df = pd.DataFrame(results)
            log_loss, brier = self._probability_scores(df)
            mae_home = float(np.mean(np.abs(df["actual_home_goals"] - df["predicted_home_goals"])))
            mae_away = float(np.mean(np.abs(df["actual_away_goals"] - df["predicted_away_goals"])))
            rows.append({
                "model": name,
                "n_predictions": int(len(df)),
                "accuracy": round(float(df["result_correct"].mean()), 4),
                "log_loss": round(log_loss, 4),
                "brier_score": round(brier, 4),
                "mae_goals_avg": round((mae_home + mae_away) / 2, 3),
            })
        return rows
