import numpy as np
from scipy.optimize import minimize
from scipy.stats import poisson
from datetime import datetime
from app import db
from app.models.database import Match, Team, Season


class DixonColesModel:
    """Modelo Dixon-Coles (1997) para predição de placares.

    Estima parâmetros de ataque/defesa por time com decaimento temporal
    e correção para placares baixos (rho).
    """

    def __init__(self, decay_lambda=0.005):
        self.decay_lambda = decay_lambda
        self.params = None
        self.teams = []
        self.team_index = {}

    def _tau(self, x, y, lambda_home, lambda_away, rho):
        """Correção de Dixon-Coles para placares baixos."""
        if x == 0 and y == 0:
            return 1 - lambda_home * lambda_away * rho
        elif x == 0 and y == 1:
            return 1 + lambda_home * rho
        elif x == 1 and y == 0:
            return 1 + lambda_away * rho
        elif x == 1 and y == 1:
            return 1 - rho
        else:
            return 1.0

    def _log_likelihood(self, params, matches_data, weights):
        """Função de log-verossimilhança negativa (para minimizar)."""
        n_teams = len(self.teams)
        attack = params[:n_teams]
        defense = params[n_teams: 2 * n_teams]
        home_adv = params[2 * n_teams]
        rho = params[2 * n_teams + 1]

        log_lik = 0.0

        for i, (home_idx, away_idx, home_goals, away_goals) in enumerate(matches_data):
            lambda_home = np.exp(attack[home_idx] + defense[away_idx] + home_adv)
            lambda_away = np.exp(attack[away_idx] + defense[home_idx])

            # Evitar lambdas muito pequenos ou grandes
            lambda_home = np.clip(lambda_home, 0.01, 10.0)
            lambda_away = np.clip(lambda_away, 0.01, 10.0)

            tau = self._tau(home_goals, away_goals, lambda_home, lambda_away, rho)

            if tau <= 0:
                tau = 1e-10

            p_home = poisson.pmf(home_goals, lambda_home)
            p_away = poisson.pmf(away_goals, lambda_away)

            prob = tau * p_home * p_away

            if prob <= 0:
                prob = 1e-10

            log_lik += weights[i] * np.log(prob)

        # Regularização L2 leve para estabilidade
        reg = 0.001 * (np.sum(attack**2) + np.sum(defense**2))

        return -log_lik + reg

    def fit(self, seasons=None):
        """Treina o modelo com as partidas do banco de dados."""
        query = (
            db.session.query(Match)
            .filter(Match.status == "FT")
            .filter(Match.home_goals.isnot(None))
            .filter(Match.away_goals.isnot(None))
            .order_by(Match.date)
        )

        if seasons:
            query = query.join(Season).filter(Season.year.in_(seasons))

        matches = query.all()

        if len(matches) < 20:
            raise ValueError(f"Dados insuficientes para treinar ({len(matches)} partidas)")

        # Mapear times
        team_ids = set()
        for m in matches:
            team_ids.add(m.home_team_id)
            team_ids.add(m.away_team_id)

        self.teams = sorted(team_ids)
        self.team_index = {t: i for i, t in enumerate(self.teams)}

        # Preparar dados
        now = datetime.utcnow()
        matches_data = []
        weights = []

        for m in matches:
            home_idx = self.team_index[m.home_team_id]
            away_idx = self.team_index[m.away_team_id]
            matches_data.append((home_idx, away_idx, m.home_goals, m.away_goals))

            days_ago = (now - m.date).days
            weights.append(np.exp(-self.decay_lambda * days_ago))

        n_teams = len(self.teams)
        # Parâmetros iniciais: attack=0, defense=0, home_adv=0.25, rho=-0.05
        x0 = np.zeros(2 * n_teams + 2)
        x0[2 * n_teams] = 0.25  # home advantage
        x0[2 * n_teams + 1] = -0.05  # rho

        # Constraint: soma dos ataques = 0 (identificabilidade)
        constraints = [
            {"type": "eq", "fun": lambda p: np.sum(p[:n_teams])},
        ]

        # Bounds para rho
        bounds = [(None, None)] * (2 * n_teams + 1)
        bounds.append((-0.5, 0.5))  # rho entre -0.5 e 0.5

        result = minimize(
            self._log_likelihood,
            x0,
            args=(matches_data, weights),
            method="SLSQP",
            constraints=constraints,
            bounds=bounds,
            options={"maxiter": 500, "ftol": 1e-8},
        )

        if not result.success:
            print(f"Aviso: otimização não convergiu completamente: {result.message}")

        self.params = result.x
        return self

    def predict(self, home_team_id, away_team_id, max_goals=7):
        """Gera predição completa para um confronto."""
        if self.params is None:
            raise ValueError("Modelo não treinado. Chame fit() primeiro.")

        if home_team_id not in self.team_index or away_team_id not in self.team_index:
            raise ValueError("Time não encontrado nos dados de treino")

        n_teams = len(self.teams)
        attack = self.params[:n_teams]
        defense = self.params[n_teams: 2 * n_teams]
        home_adv = self.params[2 * n_teams]
        rho = self.params[2 * n_teams + 1]

        h_idx = self.team_index[home_team_id]
        a_idx = self.team_index[away_team_id]

        lambda_home = np.exp(attack[h_idx] + defense[a_idx] + home_adv)
        lambda_away = np.exp(attack[a_idx] + defense[h_idx])

        lambda_home = np.clip(lambda_home, 0.01, 10.0)
        lambda_away = np.clip(lambda_away, 0.01, 10.0)

        # Matriz de probabilidade de placares
        score_matrix = np.zeros((max_goals + 1, max_goals + 1))
        for i in range(max_goals + 1):
            for j in range(max_goals + 1):
                tau = self._tau(i, j, lambda_home, lambda_away, rho)
                score_matrix[i][j] = tau * poisson.pmf(i, lambda_home) * poisson.pmf(j, lambda_away)

        # Normalizar
        score_matrix /= score_matrix.sum()

        # Probabilidades de resultado
        home_win = np.sum(np.tril(score_matrix, -1))
        draw = np.sum(np.diag(score_matrix))
        away_win = np.sum(np.triu(score_matrix, 1))

        # Over/Under
        total_goals_probs = {}
        for threshold in [0.5, 1.5, 2.5, 3.5]:
            over_prob = 0.0
            for i in range(max_goals + 1):
                for j in range(max_goals + 1):
                    if i + j > threshold:
                        over_prob += score_matrix[i][j]
            total_goals_probs[threshold] = over_prob

        # BTTS - P(home > 0) * P(away > 0) corrigido pela matriz
        btts_prob = 0.0
        for i in range(1, max_goals + 1):
            for j in range(1, max_goals + 1):
                btts_prob += score_matrix[i][j]

        # Placar mais provável
        most_likely = np.unravel_index(score_matrix.argmax(), score_matrix.shape)

        # Confiança
        max_result_prob = max(home_win, draw, away_win)
        if max_result_prob >= 0.55:
            confidence = "alta"
        elif max_result_prob >= 0.42:
            confidence = "media"
        else:
            confidence = "baixa"

        return {
            "lambda_home": float(lambda_home),
            "lambda_away": float(lambda_away),
            "home_win_prob": float(home_win),
            "draw_prob": float(draw),
            "away_win_prob": float(away_win),
            "over_05": float(total_goals_probs[0.5]),
            "over_15": float(total_goals_probs[1.5]),
            "over_25": float(total_goals_probs[2.5]),
            "over_35": float(total_goals_probs[3.5]),
            "btts_prob": float(btts_prob),
            "most_likely_score": {"home": int(most_likely[0]), "away": int(most_likely[1])},
            "score_matrix": score_matrix.tolist(),
            "confidence": confidence,
        }

    def get_team_strengths(self):
        """Retorna ataque e defesa de cada time (para análise)."""
        if self.params is None:
            return {}

        n_teams = len(self.teams)
        attack = self.params[:n_teams]
        defense = self.params[n_teams: 2 * n_teams]

        strengths = {}
        for team_id, idx in self.team_index.items():
            team = Team.query.get(team_id)
            strengths[team.name if team else str(team_id)] = {
                "attack": float(attack[idx]),
                "defense": float(defense[idx]),
            }

        return strengths

    def get_home_advantage(self):
        if self.params is None:
            return 0
        return float(self.params[2 * len(self.teams)])
