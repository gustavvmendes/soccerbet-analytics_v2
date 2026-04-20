"""
Motor de predição ao vivo para partidas em andamento.

Combina:
1. Poisson ajustado por tempo — dado o placar atual e tempo restante,
   recalcula λ remanescente para cada time.
2. Modificadores de contexto — cartões vermelhos, desempenho acima/abaixo
   do esperado (chutes, posse, etc.).
3. xG acumulado — estimativa de gols esperados a partir dos chutes reais.
4. Momentum — tendência de quem está atacando mais nos últimos minutos.
5. Over/Under dinâmico — probabilidades atualizadas com gols já marcados.
6. Próximo gol — probabilidade de cada time marcar o próximo gol.
"""

import numpy as np
from scipy.stats import poisson


class LivePredictor:
    """Calcula probabilidades ao vivo usando Poisson ajustado + contexto."""

    # ── xG por tipo de finalização (baseado em pesquisa acadêmica) ──
    XG_SHOT_ON_TARGET = 0.32
    XG_SHOT_OFF_TARGET = 0.03
    XG_BLOCKED_SHOT = 0.05

    # ── Impacto de cartão vermelho ──
    # Pesquisas mostram redução de ~25-30% na taxa de gol com 1 jogador a menos
    RED_CARD_MODIFIER = 0.72  # multiplicador por cartão vermelho

    # ── Peso do ajuste por performance ao vivo ──
    PERFORMANCE_WEIGHT = 0.25  # quão forte as stats ao vivo influenciam

    def calculate_live_probabilities(
        self,
        pre_match_lambda_home: float,
        pre_match_lambda_away: float,
        current_home_goals: int,
        current_away_goals: int,
        elapsed_minutes: int,
        home_red_cards: int = 0,
        away_red_cards: int = 0,
        home_shots_on_target: int = 0,
        away_shots_on_target: int = 0,
        home_shots_total: int = 0,
        away_shots_total: int = 0,
        home_possession: float = 50.0,
        away_possession: float = 50.0,
        home_corners: int = 0,
        away_corners: int = 0,
        home_dangerous_attacks: int = 0,
        away_dangerous_attacks: int = 0,
        max_goals: int = 8,
    ) -> dict:
        """
        Retorna probabilidades atualizadas de resultado, over/under, xG, etc.
        """
        # ── 1. Fração de tempo restante ──
        effective_elapsed = min(elapsed_minutes, 95)
        remaining_fraction = max((90 - effective_elapsed) / 90, 0.01)
        elapsed_fraction = 1 - remaining_fraction

        # ── 2. Cartões vermelhos ──
        home_red_mod = self.RED_CARD_MODIFIER ** home_red_cards
        away_red_mod = self.RED_CARD_MODIFIER ** away_red_cards

        # ── 3. Ajuste por performance ao vivo ──
        home_perf_mod = self._performance_modifier(
            pre_match_lambda_home, elapsed_fraction,
            home_shots_on_target, home_shots_total,
            home_possession, home_dangerous_attacks,
        )
        away_perf_mod = self._performance_modifier(
            pre_match_lambda_away, elapsed_fraction,
            away_shots_on_target, away_shots_total,
            away_possession, away_dangerous_attacks,
        )

        # ── 4. Lambda remanescente ──
        lambda_h_remaining = (
            pre_match_lambda_home * remaining_fraction
            * home_red_mod * home_perf_mod
        )
        lambda_a_remaining = (
            pre_match_lambda_away * remaining_fraction
            * away_red_mod * away_perf_mod
        )

        lambda_h_remaining = np.clip(lambda_h_remaining, 0.01, 10.0)
        lambda_a_remaining = np.clip(lambda_a_remaining, 0.01, 10.0)

        # ── 5. Probabilidades de resultado final ──
        home_win_prob = 0.0
        draw_prob = 0.0
        away_win_prob = 0.0

        for extra_h in range(max_goals + 1):
            for extra_a in range(max_goals + 1):
                p = (poisson.pmf(extra_h, lambda_h_remaining)
                     * poisson.pmf(extra_a, lambda_a_remaining))
                final_h = current_home_goals + extra_h
                final_a = current_away_goals + extra_a
                if final_h > final_a:
                    home_win_prob += p
                elif final_h == final_a:
                    draw_prob += p
                else:
                    away_win_prob += p

        # Normalizar
        total = home_win_prob + draw_prob + away_win_prob
        if total > 0:
            home_win_prob /= total
            draw_prob /= total
            away_win_prob /= total

        # ── 6. Over/Under dinâmico ──
        current_total = current_home_goals + current_away_goals
        lambda_total_remaining = lambda_h_remaining + lambda_a_remaining

        over_under = {}
        for threshold in [0.5, 1.5, 2.5, 3.5, 4.5]:
            remaining_needed = threshold - current_total
            if remaining_needed <= 0:
                over_under[f"over_{str(threshold).replace('.', '_')}"] = 1.0
            else:
                k = int(remaining_needed)
                over_prob = 1 - self._poisson_cdf(k, lambda_total_remaining)
                over_under[f"over_{str(threshold).replace('.', '_')}"] = float(over_prob)

        # ── 7. xG acumulado ──
        home_xg = self._calculate_xg(home_shots_on_target,
                                      home_shots_total - home_shots_on_target, 0)
        away_xg = self._calculate_xg(away_shots_on_target,
                                      away_shots_total - away_shots_on_target, 0)

        # ── 8. Próximo gol ──
        total_rate = lambda_h_remaining + lambda_a_remaining
        if total_rate > 0 and remaining_fraction > 0.02:
            next_goal_home = lambda_h_remaining / total_rate
            next_goal_away = lambda_a_remaining / total_rate
            # Probabilidade de nenhum gol adicional
            no_more_goals = (poisson.pmf(0, lambda_h_remaining)
                             * poisson.pmf(0, lambda_a_remaining))
        else:
            next_goal_home = 0.5
            next_goal_away = 0.5
            no_more_goals = 1.0

        # ── 9. BTTS atualizado ──
        home_already_scored = current_home_goals > 0
        away_already_scored = current_away_goals > 0
        if home_already_scored and away_already_scored:
            btts_prob = 1.0
        elif home_already_scored:
            # Falta o visitante marcar
            btts_prob = 1 - poisson.pmf(0, lambda_a_remaining)
        elif away_already_scored:
            btts_prob = 1 - poisson.pmf(0, lambda_h_remaining)
        else:
            btts_prob = ((1 - poisson.pmf(0, lambda_h_remaining))
                         * (1 - poisson.pmf(0, lambda_a_remaining)))

        # ── 10. Placar mais provável ── 
        best_score = None
        best_prob = 0
        for extra_h in range(max_goals + 1):
            for extra_a in range(max_goals + 1):
                p = (poisson.pmf(extra_h, lambda_h_remaining)
                     * poisson.pmf(extra_a, lambda_a_remaining))
                if p > best_prob:
                    best_prob = p
                    best_score = (
                        current_home_goals + extra_h,
                        current_away_goals + extra_a,
                    )

        return {
            "home_win_prob": round(float(home_win_prob), 4),
            "draw_prob": round(float(draw_prob), 4),
            "away_win_prob": round(float(away_win_prob), 4),
            "lambda_home_remaining": round(float(lambda_h_remaining), 3),
            "lambda_away_remaining": round(float(lambda_a_remaining), 3),
            "over_under": {k: round(v, 4) for k, v in over_under.items()},
            "home_xg": round(float(home_xg), 2),
            "away_xg": round(float(away_xg), 2),
            "next_goal": {
                "home": round(float(next_goal_home), 4),
                "away": round(float(next_goal_away), 4),
                "no_more_goals": round(float(no_more_goals), 4),
            },
            "btts_prob": round(float(btts_prob), 4),
            "most_likely_final_score": {
                "home": best_score[0] if best_score else current_home_goals,
                "away": best_score[1] if best_score else current_away_goals,
            },
            "modifiers": {
                "home_red_cards": home_red_cards,
                "away_red_cards": away_red_cards,
                "home_performance": round(float(home_perf_mod), 3),
                "away_performance": round(float(away_perf_mod), 3),
                "remaining_fraction": round(float(remaining_fraction), 3),
            },
        }

    def calculate_momentum(self, snapshots: list[dict]) -> dict:
        """
        Calcula momentum a partir dos snapshots recentes.
        Compara os últimos 10 minutos com os anteriores.
        """
        if len(snapshots) < 2:
            return {"home": 50, "away": 50, "trend": "stable"}

        recent = snapshots[-1]
        previous = snapshots[-2] if len(snapshots) >= 2 else snapshots[0]

        # Diferença de chutes, posse, escanteios
        h_shots_delta = (recent.get("home_shots_total", 0)
                         - previous.get("home_shots_total", 0))
        a_shots_delta = (recent.get("away_shots_total", 0)
                         - previous.get("away_shots_total", 0))
        h_corners_delta = (recent.get("home_corners", 0)
                           - previous.get("home_corners", 0))
        a_corners_delta = (recent.get("away_corners", 0)
                           - previous.get("away_corners", 0))
        h_danger_delta = (recent.get("home_dangerous_attacks", 0)
                          - previous.get("home_dangerous_attacks", 0))
        a_danger_delta = (recent.get("away_dangerous_attacks", 0)
                          - previous.get("away_dangerous_attacks", 0))

        # Momentum score: chutes × 3 + escanteios × 2 + ataques perigosos × 1
        home_score = h_shots_delta * 3 + h_corners_delta * 2 + h_danger_delta
        away_score = a_shots_delta * 3 + a_corners_delta * 2 + a_danger_delta
        total = home_score + away_score or 1

        home_momentum = 50 + 50 * (home_score - away_score) / max(total, 1)
        home_momentum = np.clip(home_momentum, 10, 90)
        away_momentum = 100 - home_momentum

        diff = home_score - away_score
        trend = ("home_pressing" if diff > 3
                 else "away_pressing" if diff < -3
                 else "stable")

        return {
            "home": round(float(home_momentum)),
            "away": round(float(away_momentum)),
            "trend": trend,
            "home_activity": {
                "shots": h_shots_delta,
                "corners": h_corners_delta,
                "dangerous_attacks": h_danger_delta,
            },
            "away_activity": {
                "shots": a_shots_delta,
                "corners": a_corners_delta,
                "dangerous_attacks": a_danger_delta,
            },
        }

    def generate_live_insights(
        self,
        live_probs: dict,
        pre_match: dict,
        elapsed: int,
        home_name: str,
        away_name: str,
        home_goals: int,
        away_goals: int,
        home_red: int,
        away_red: int,
        momentum: dict,
    ) -> list[dict]:
        """Gera explicações textuais sobre a situação atual ao vivo."""
        insights = []

        # Mudança de probabilidade vs pré-jogo
        pre_hw = pre_match.get("home_win_prob", 0.33)
        live_hw = live_probs["home_win_prob"]
        shift = (live_hw - pre_hw) * 100

        if abs(shift) > 10:
            direction = "aumentou" if shift > 0 else "caiu"
            insights.append({
                "type": "probability_shift",
                "text": (f"Chance de vitória do {home_name} {direction} "
                         f"{abs(shift):.0f}pp desde o pré-jogo "
                         f"({pre_hw*100:.0f}% → {live_hw*100:.0f}%)"),
                "severity": "high",
            })

        # Cartões vermelhos
        if home_red > 0:
            reduction = (1 - self.RED_CARD_MODIFIER ** home_red) * 100
            insights.append({
                "type": "red_card",
                "text": (f"⚠️ {home_name} com {home_red} expulsão(ões) — "
                         f"capacidade ofensiva reduzida em ~{reduction:.0f}%"),
                "severity": "critical",
            })
        if away_red > 0:
            reduction = (1 - self.RED_CARD_MODIFIER ** away_red) * 100
            insights.append({
                "type": "red_card",
                "text": (f"⚠️ {away_name} com {away_red} expulsão(ões) — "
                         f"capacidade ofensiva reduzida em ~{reduction:.0f}%"),
                "severity": "critical",
            })

        # xG vs Gols reais
        home_xg = live_probs.get("home_xg", 0)
        away_xg = live_probs.get("away_xg", 0)
        if home_goals > home_xg + 0.5:
            insights.append({
                "type": "xg_overperformance",
                "text": (f"{home_name} está marcando acima do esperado: "
                         f"{home_goals} gols vs {home_xg:.1f} xG"),
                "severity": "medium",
            })
        elif home_goals < home_xg - 0.8:
            insights.append({
                "type": "xg_underperformance",
                "text": (f"{home_name} está abaixo do esperado: "
                         f"{home_goals} gols vs {home_xg:.1f} xG — pode empatar/virar"),
                "severity": "medium",
            })
        if away_goals > away_xg + 0.5:
            insights.append({
                "type": "xg_overperformance",
                "text": (f"{away_name} está marcando acima do esperado: "
                         f"{away_goals} gols vs {away_xg:.1f} xG"),
                "severity": "medium",
            })

        # Momentum
        if momentum.get("trend") == "home_pressing":
            insights.append({
                "type": "momentum",
                "text": f"📈 {home_name} está pressionando — dominando a posse recente",
                "severity": "low",
            })
        elif momentum.get("trend") == "away_pressing":
            insights.append({
                "type": "momentum",
                "text": f"📈 {away_name} está pressionando — dominando a posse recente",
                "severity": "low",
            })

        # Tempo restante
        remaining = 90 - elapsed
        if remaining <= 15 and home_goals != away_goals:
            leader = home_name if home_goals > away_goals else away_name
            prob = max(live_probs["home_win_prob"], live_probs["away_win_prob"])
            insights.append({
                "type": "time_pressure",
                "text": (f"⏱️ Últimos {remaining} minutos — {leader} "
                         f"lidera com {prob*100:.0f}% de chance de vitória"),
                "severity": "high",
            })
        elif remaining <= 15 and home_goals == away_goals:
            insights.append({
                "type": "time_pressure",
                "text": (f"⏱️ Últimos {remaining} minutos empatados — "
                         f"empate com {live_probs['draw_prob']*100:.0f}% de chance de se manter"),
                "severity": "high",
            })

        return insights

    # ── Métodos auxiliares ──────────────────────────────

    def _performance_modifier(
        self, pre_lambda, elapsed_frac,
        shots_on_target, shots_total, possession, dangerous_attacks,
    ):
        """
        Compara desempenho real vs esperado e gera modificador.
        Se o time está chutando mais que o esperado, aumenta o λ.
        """
        if elapsed_frac < 0.05:
            return 1.0  # Jogo muito no início, sem dados suficientes

        # Chutes esperados até agora
        # Média da Série A: ~12 chutes/time por jogo, ~4 no gol
        expected_shots_total = 12.0 * elapsed_frac
        expected_shots_on = 4.0 * elapsed_frac

        if expected_shots_total < 1:
            return 1.0

        shot_ratio = shots_total / max(expected_shots_total, 1)
        sot_ratio = shots_on_target / max(expected_shots_on, 0.5)

        # Posse: 50% = neutro, mais = leve bônus
        possession_mod = 1.0 + (possession - 50) * 0.003

        # Combinar
        raw = (0.4 * shot_ratio + 0.4 * sot_ratio + 0.2 * possession_mod)
        # Suavizar: não deixar modificar mais que ±30%
        modifier = 1.0 + self.PERFORMANCE_WEIGHT * (raw - 1.0)
        return float(np.clip(modifier, 0.7, 1.3))

    def _calculate_xg(self, shots_on, shots_off, blocked):
        """Calcula xG a partir dos chutes."""
        return (shots_on * self.XG_SHOT_ON_TARGET
                + shots_off * self.XG_SHOT_OFF_TARGET
                + blocked * self.XG_BLOCKED_SHOT)

    @staticmethod
    def _poisson_cdf(k, lam):
        """CDF da Poisson: P(X <= k)."""
        cdf = 0.0
        term = np.exp(-lam)
        cdf += term
        for i in range(1, k + 1):
            term *= lam / i
            cdf += term
        return cdf
