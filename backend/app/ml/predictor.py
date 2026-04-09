import json
import os
import joblib
import numpy as np
from flask import current_app
from app import db
from app.models.database import Team, League, Prediction, Player, PlayerSeasonStats
from app.ml.dixon_coles import DixonColesModel
from app.ml.xgboost_models import XGBoostModels
from app.ml.feature_engineering import FeatureEngineering


class Predictor:
    """Orquestra Dixon-Coles + XGBoost para predição completa."""

    def __init__(self):
        self.dc_model = None
        self.xgb_models = None
        self.fe = FeatureEngineering()

    def train(self, seasons=None):
        """Treina todos os modelos."""
        print("=== Treinando Dixon-Coles ===")
        self.dc_model = DixonColesModel()
        self.dc_model.fit(seasons)
        print(f"  Vantagem de casa: {self.dc_model.get_home_advantage():.3f}")
        print(f"  Times treinados: {len(self.dc_model.teams)}")

        print("\n=== Construindo dataset de features ===")
        df = self.fe.build_dataset(seasons)
        print(f"  Amostras: {len(df)}")

        if len(df) < 30:
            raise ValueError(f"Dataset muito pequeno ({len(df)} amostras)")

        print("\n=== Treinando XGBoost ===")
        self.xgb_models = XGBoostModels()
        self.xgb_models.train(df)

        # Salvar modelos
        models_dir = current_app.config["ML_MODELS_DIR"]
        os.makedirs(models_dir, exist_ok=True)

        joblib.dump(
            {"params": self.dc_model.params, "teams": self.dc_model.teams, "team_index": self.dc_model.team_index},
            os.path.join(models_dir, "dixon_coles.joblib"),
        )
        self.xgb_models.save(models_dir)

        print("\n=== Modelos salvos ===")
        return {
            "dixon_coles": {
                "home_advantage": self.dc_model.get_home_advantage(),
                "teams_count": len(self.dc_model.teams),
                "team_strengths": self.dc_model.get_team_strengths(),
            },
            "xgboost": {
                "models_count": len(self.xgb_models.models),
                "metrics": self.xgb_models.metrics,
                "feature_importance": self.xgb_models.get_feature_importance(top_n=5),
            },
            "dataset_size": len(df),
        }

    def load(self):
        """Carrega modelos salvos."""
        models_dir = current_app.config["ML_MODELS_DIR"]

        dc_path = os.path.join(models_dir, "dixon_coles.joblib")
        if not os.path.exists(dc_path):
            raise FileNotFoundError("Modelos não encontrados. Treine primeiro via /api/data/train")

        dc_data = joblib.load(dc_path)
        self.dc_model = DixonColesModel()
        self.dc_model.params = dc_data["params"]
        self.dc_model.teams = dc_data["teams"]
        self.dc_model.team_index = dc_data["team_index"]

        self.xgb_models = XGBoostModels()
        self.xgb_models.load(models_dir)

    def predict(self, home_team_api_id, away_team_api_id, save=True):
        """Gera predição completa para um confronto."""
        if self.dc_model is None:
            self.load()

        home_team = Team.query.filter_by(api_id=home_team_api_id).first()
        away_team = Team.query.filter_by(api_id=away_team_api_id).first()

        if not home_team or not away_team:
            raise ValueError("Time não encontrado no banco de dados")

        # Dixon-Coles: gols, resultado, over/under, btts
        dc_result = self.dc_model.predict(home_team.id, away_team.id)

        # XGBoost: escanteios, cartões, posse, chutes
        features = self.fe.compute_prediction_features(home_team_api_id, away_team_api_id)
        xgb_result = self.xgb_models.predict(features) if features else {}

        result = {
            **dc_result,
            "xgb_predictions": xgb_result,
            "home_team": home_team.to_dict(),
            "away_team": away_team.to_dict(),
        }

        if save:
            self._save_prediction(home_team, away_team, dc_result, xgb_result)

        return result

    def _save_prediction(self, home_team, away_team, dc_result, xgb_result):
        league = League.query.filter_by(api_id=71).first()
        if not league:
            return

        prediction = Prediction(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            league_id=league.id,
            home_win_prob=dc_result["home_win_prob"],
            draw_prob=dc_result["draw_prob"],
            away_win_prob=dc_result["away_win_prob"],
            predicted_home_goals=dc_result["lambda_home"],
            predicted_away_goals=dc_result["lambda_away"],
            over_05_prob=dc_result["over_05"],
            over_15_prob=dc_result["over_15"],
            over_25_prob=dc_result["over_25"],
            over_35_prob=dc_result["over_35"],
            btts_prob=dc_result["btts_prob"],
            predicted_home_corners=xgb_result.get("home_corners"),
            predicted_away_corners=xgb_result.get("away_corners"),
            predicted_home_cards=xgb_result.get("home_cards"),
            predicted_away_cards=xgb_result.get("away_cards"),
            predicted_home_possession=xgb_result.get("home_possession"),
            predicted_away_possession=xgb_result.get("away_possession"),
            predicted_home_shots=xgb_result.get("home_shots"),
            predicted_away_shots=xgb_result.get("away_shots"),
            score_matrix=json.dumps(dc_result["score_matrix"]),
            confidence=dc_result["confidence"],
        )

        db.session.add(prediction)
        db.session.commit()

    def get_metrics(self):
        """Retorna métricas dos modelos para análise."""
        if self.dc_model is None:
            self.load()

        return {
            "dixon_coles": {
                "home_advantage": self.dc_model.get_home_advantage(),
                "team_strengths": self.dc_model.get_team_strengths(),
            },
            "xgboost": {
                "metrics": self.xgb_models.metrics,
                "feature_importance": self.xgb_models.get_feature_importance(),
            },
        }

    def get_explanation(self, home_team_api_id, away_team_api_id):
        """Gera explicação detalhada do porquê de cada predição."""
        if self.dc_model is None:
            self.load()

        home_team = Team.query.filter_by(api_id=home_team_api_id).first()
        away_team = Team.query.filter_by(api_id=away_team_api_id).first()

        if not home_team or not away_team:
            raise ValueError("Time não encontrado")

        explanation = {
            "dixon_coles": self._explain_dixon_coles(home_team, away_team),
            "features": self._explain_features(home_team_api_id, away_team_api_id),
            "key_factors": [],
        }

        # Gerar fatores-chave em linguagem natural
        explanation["key_factors"] = self._generate_key_factors(
            home_team, away_team, explanation
        )

        return explanation

    def _explain_dixon_coles(self, home_team, away_team):
        """Explica os parâmetros do Dixon-Coles para o confronto."""
        import numpy as np

        n_teams = len(self.dc_model.teams)
        attack = self.dc_model.params[:n_teams]
        defense = self.dc_model.params[n_teams: 2 * n_teams]
        home_adv = self.dc_model.params[2 * n_teams]

        h_idx = self.dc_model.team_index.get(home_team.id)
        a_idx = self.dc_model.team_index.get(away_team.id)

        if h_idx is None or a_idx is None:
            return None

        # Médias da liga
        avg_attack = float(np.mean(attack))
        avg_defense = float(np.mean(defense))

        # Rankings
        attack_sorted = sorted(self.dc_model.team_index.items(),
                               key=lambda x: attack[x[1]], reverse=True)
        defense_sorted = sorted(self.dc_model.team_index.items(),
                                key=lambda x: defense[x[1]])  # menor = melhor defesa

        h_attack_rank = next(i + 1 for i, (tid, _) in enumerate(attack_sorted) if tid == home_team.id)
        h_defense_rank = next(i + 1 for i, (tid, _) in enumerate(defense_sorted) if tid == home_team.id)
        a_attack_rank = next(i + 1 for i, (tid, _) in enumerate(attack_sorted) if tid == away_team.id)
        a_defense_rank = next(i + 1 for i, (tid, _) in enumerate(defense_sorted) if tid == away_team.id)

        total_teams = len(self.dc_model.teams)

        lambda_home = float(np.exp(attack[h_idx] + defense[a_idx] + home_adv))
        lambda_away = float(np.exp(attack[a_idx] + defense[h_idx]))

        return {
            "home_attack": float(attack[h_idx]),
            "home_defense": float(defense[h_idx]),
            "away_attack": float(attack[a_idx]),
            "away_defense": float(defense[a_idx]),
            "home_advantage": float(home_adv),
            "home_advantage_pct": float((np.exp(home_adv) - 1) * 100),
            "league_avg_attack": avg_attack,
            "league_avg_defense": avg_defense,
            "home_attack_rank": h_attack_rank,
            "home_defense_rank": h_defense_rank,
            "away_attack_rank": a_attack_rank,
            "away_defense_rank": a_defense_rank,
            "total_teams": total_teams,
            "lambda_home": lambda_home,
            "lambda_away": lambda_away,
            "formula_home": f"exp({attack[h_idx]:.3f} + {defense[a_idx]:.3f} + {home_adv:.3f}) = {lambda_home:.2f}",
            "formula_away": f"exp({attack[a_idx]:.3f} + {defense[h_idx]:.3f}) = {lambda_away:.2f}",
        }

    def _explain_features(self, home_team_api_id, away_team_api_id):
        """Explica as features usadas pelo XGBoost."""
        features = self.fe.compute_prediction_features(home_team_api_id, away_team_api_id)
        if not features:
            return None

        # Organizar features em categorias legíveis
        home_form = {
            "avg_goals_scored": features.get("home_avg_goals_scored", 0),
            "avg_goals_conceded": features.get("home_avg_goals_conceded", 0),
            "avg_shots": features.get("home_avg_shots", 0),
            "avg_corners": features.get("home_avg_corners", 0),
            "avg_cards": features.get("home_avg_cards", 0),
            "avg_possession": features.get("home_avg_possession", 0),
            "win_rate": features.get("home_win_rate", 0),
            "draw_rate": features.get("home_draw_rate", 0),
            "loss_rate": features.get("home_loss_rate", 0),
            "clean_sheet_rate": features.get("home_clean_sheet_rate", 0),
        }

        home_as_home = {
            "avg_goals_scored": features.get("home_as_home_avg_goals_scored", 0),
            "avg_goals_conceded": features.get("home_as_home_avg_goals_conceded", 0),
            "avg_shots": features.get("home_as_home_avg_shots", 0),
            "avg_corners": features.get("home_as_home_avg_corners", 0),
            "avg_cards": features.get("home_as_home_avg_cards", 0),
            "avg_possession": features.get("home_as_home_avg_possession", 0),
            "win_rate": features.get("home_as_home_win_rate", 0),
        }

        away_form = {
            "avg_goals_scored": features.get("away_avg_goals_scored", 0),
            "avg_goals_conceded": features.get("away_avg_goals_conceded", 0),
            "avg_shots": features.get("away_avg_shots", 0),
            "avg_corners": features.get("away_avg_corners", 0),
            "avg_cards": features.get("away_avg_cards", 0),
            "avg_possession": features.get("away_avg_possession", 0),
            "win_rate": features.get("away_win_rate", 0),
            "draw_rate": features.get("away_draw_rate", 0),
            "loss_rate": features.get("away_loss_rate", 0),
            "clean_sheet_rate": features.get("away_clean_sheet_rate", 0),
        }

        away_as_away = {
            "avg_goals_scored": features.get("away_as_away_avg_goals_scored", 0),
            "avg_goals_conceded": features.get("away_as_away_avg_goals_conceded", 0),
            "avg_shots": features.get("away_as_away_avg_shots", 0),
            "avg_corners": features.get("away_as_away_avg_corners", 0),
            "avg_cards": features.get("away_as_away_avg_cards", 0),
            "avg_possession": features.get("away_as_away_avg_possession", 0),
            "win_rate": features.get("away_as_away_win_rate", 0),
        }

        h2h = {
            "home_wins": features.get("h2h_home_wins", 0),
            "draws": features.get("h2h_draws", 0),
            "away_wins": features.get("h2h_away_wins", 0),
            "avg_total_goals": features.get("h2h_avg_total_goals", 0),
            "matches_count": features.get("h2h_matches_count", 0),
        }

        return {
            "home_form": home_form,
            "home_as_home": home_as_home,
            "away_form": away_form,
            "away_as_away": away_as_away,
            "h2h": h2h,
        }

    def _generate_key_factors(self, home_team, away_team, explanation):
        """Gera fatores-chave em linguagem natural."""
        factors = []
        dc = explanation.get("dixon_coles")
        feat = explanation.get("features")

        if dc:
            total = dc["total_teams"]

            # Ataque do mandante
            if dc["home_attack_rank"] <= 5:
                factors.append({
                    "type": "positive_home",
                    "text": f"{home_team.name} tem o {dc['home_attack_rank']}º melhor ataque do campeonato (param: {dc['home_attack']:.3f})",
                })
            elif dc["home_attack_rank"] >= total - 4:
                factors.append({
                    "type": "negative_home",
                    "text": f"{home_team.name} tem o {dc['home_attack_rank']}º ataque (entre os piores) — param: {dc['home_attack']:.3f}",
                })

            # Defesa do visitante
            if dc["away_defense_rank"] >= total - 4:
                factors.append({
                    "type": "positive_home",
                    "text": f"{away_team.name} tem a {dc['away_defense_rank']}ª defesa (fraca) — facilita gols do mandante",
                })
            elif dc["away_defense_rank"] <= 5:
                factors.append({
                    "type": "negative_home",
                    "text": f"{away_team.name} tem a {dc['away_defense_rank']}ª melhor defesa — dificulta gols do mandante",
                })

            # Ataque do visitante
            if dc["away_attack_rank"] <= 5:
                factors.append({
                    "type": "positive_away",
                    "text": f"{away_team.name} tem o {dc['away_attack_rank']}º melhor ataque (param: {dc['away_attack']:.3f})",
                })

            # Vantagem de jogar em casa
            factors.append({
                "type": "info",
                "text": f"Mando de campo dá bônus de +{dc['home_advantage_pct']:.0f}% nos gols esperados do mandante",
            })

            # Fórmulas
            factors.append({
                "type": "formula",
                "text": f"λ {home_team.name} = {dc['formula_home']} gols esperados",
            })
            factors.append({
                "type": "formula",
                "text": f"λ {away_team.name} = {dc['formula_away']} gols esperados",
            })

        if feat:
            hf = feat.get("home_form", {})
            af = feat.get("away_form", {})
            hh = feat.get("home_as_home", {})
            aa = feat.get("away_as_away", {})
            h2h = feat.get("h2h", {})

            # Forma recente como mandante
            if hh.get("win_rate", 0) >= 0.6:
                factors.append({
                    "type": "positive_home",
                    "text": f"{home_team.name} vence {hh['win_rate']*100:.0f}% dos jogos como mandante (últimos 5)",
                })

            # Forma recente como visitante
            if aa.get("win_rate", 0) <= 0.2:
                factors.append({
                    "type": "positive_home",
                    "text": f"{away_team.name} vence apenas {aa['win_rate']*100:.0f}% dos jogos como visitante",
                })
            elif aa.get("win_rate", 0) >= 0.6:
                factors.append({
                    "type": "positive_away",
                    "text": f"{away_team.name} vence {aa['win_rate']*100:.0f}% dos jogos como visitante",
                })

            # Média de gols
            if hf.get("avg_goals_scored", 0) >= 1.8:
                factors.append({
                    "type": "positive_home",
                    "text": f"{home_team.name} marca em média {hf['avg_goals_scored']:.1f} gols/jogo",
                })

            if af.get("avg_goals_conceded", 0) >= 1.5:
                factors.append({
                    "type": "positive_home",
                    "text": f"{away_team.name} sofre em média {af['avg_goals_conceded']:.1f} gols/jogo",
                })

            # H2H
            if h2h.get("matches_count", 0) >= 3:
                total_h2h = h2h.get("matches_count", 1)
                hw = h2h.get("home_wins", 0)
                d = h2h.get("draws", 0)
                aw = h2h.get("away_wins", 0)
                factors.append({
                    "type": "h2h",
                    "text": f"Confronto direto ({total_h2h} jogos): {hw}V {d}E {aw}D — média de {h2h.get('avg_total_goals', 0):.1f} gols",
                })

            # Chutes e escanteios para explicar XGBoost
            factors.append({
                "type": "xgboost_context",
                "text": f"{home_team.name} média de {hf.get('avg_shots', 0):.1f} chutes e {hf.get('avg_corners', 0):.1f} escanteios/jogo",
            })
            factors.append({
                "type": "xgboost_context",
                "text": f"{away_team.name} média de {af.get('avg_shots', 0):.1f} chutes e {af.get('avg_corners', 0):.1f} escanteios/jogo",
            })

        return factors

    def predict_player_match(self, player_api_id, home_team_api_id, away_team_api_id):
        """Gera predição individual de um jogador para um confronto específico."""
        if self.dc_model is None:
            self.load()

        player = Player.query.filter_by(api_id=player_api_id).first()
        if not player:
            raise ValueError("Jogador não encontrado")

        stats = PlayerSeasonStats.query.filter_by(
            player_api_id=player_api_id,
            team_api_id=player.team_api_id,
        ).order_by(PlayerSeasonStats.season.desc()).first()

        if not stats or stats.appearances == 0:
            raise ValueError("Sem estatísticas suficientes para prever")

        # Predição do time para este jogo
        team_pred = self.predict(home_team_api_id, away_team_api_id, save=False)
        xgb = team_pred.get("xgb_predictions", {})

        is_home = player.team_api_id == home_team_api_id
        team_api_id = player.team_api_id

        # Médias por jogo do jogador
        apps = stats.appearances
        per90 = stats.minutes / 90 if stats.minutes > 0 else apps  # normalizar por 90 min

        goals_per_app = stats.goals / apps
        assists_per_app = stats.assists / apps
        shots_per_app = stats.shots_total / apps
        key_passes_per_app = stats.passes_key / apps
        tackles_per_app = stats.tackles / apps
        interceptions_per_app = stats.interceptions / apps
        dribbles_per_app = stats.dribbles_success / apps
        fouls_per_app = stats.fouls_committed / apps
        yellow_per_app = stats.yellow_cards / apps
        red_per_app = stats.red_cards / apps

        # Lambda do time para gols (Dixon-Coles)
        team_lambda = team_pred["lambda_home"] if is_home else team_pred["lambda_away"]

        # Chutes previstos para o time
        team_shots = xgb.get("home_shots", 0) if is_home else xgb.get("away_shots", 0)
        team_corners = xgb.get("home_corners", 0) if is_home else xgb.get("away_corners", 0)
        team_cards = xgb.get("home_cards", 0) if is_home else xgb.get("away_cards", 0)

        # Obter totais do time na temporada para calcular contribuição
        team_player_stats = PlayerSeasonStats.query.filter_by(
            team_api_id=team_api_id, season=stats.season
        ).all()

        team_total_goals = sum(p.goals for p in team_player_stats) or 1
        team_total_shots = sum(p.shots_total for p in team_player_stats) or 1
        team_total_assists = sum(p.assists for p in team_player_stats) or 1
        team_total_key_passes = sum(p.passes_key for p in team_player_stats) or 1
        team_total_tackles = sum(p.tackles for p in team_player_stats) or 1
        team_total_yellow = sum(p.yellow_cards for p in team_player_stats) or 1

        # Contribuição percentual do jogador no time
        goal_share = stats.goals / team_total_goals
        shot_share = stats.shots_total / team_total_shots
        assist_share = stats.assists / team_total_assists if stats.assists > 0 else 0
        key_pass_share = stats.passes_key / team_total_key_passes
        tackle_share = stats.tackles / team_total_tackles
        card_share = stats.yellow_cards / team_total_yellow if stats.yellow_cards > 0 else 0

        # Probabilidade de ser titular
        starter_pct = (stats.lineups / apps) * 100 if apps > 0 else 0

        # Minutos estimados
        avg_minutes = stats.minutes / apps if apps > 0 else 0
        minute_factor = avg_minutes / 90  # fator de ajuste por minutos jogados

        # Predições para este jogo usando contribuição proporcional × predição do time
        pred_goals = team_lambda * goal_share
        pred_shots = team_shots * shot_share
        pred_assists = team_lambda * assist_share  # assists escalam com gols do time
        pred_key_passes = key_passes_per_app  # baseline do jogador
        pred_tackles = tackles_per_app
        pred_interceptions = interceptions_per_app
        pred_dribbles = dribbles_per_app
        pred_fouls = fouls_per_app
        pred_yellow = team_cards * card_share
        pred_rating = stats.rating if stats.rating else None

        # Probabilidade de gol (Poisson: P(X ≥ 1) = 1 - P(X=0))
        goal_prob = 1 - np.exp(-pred_goals)
        # Probabilidade de assistência
        assist_prob = 1 - np.exp(-pred_assists) if pred_assists > 0 else 0
        # Probabilidade de cartão amarelo
        yellow_prob = 1 - np.exp(-pred_yellow) if pred_yellow > 0 else yellow_per_app

        # Gerar explicações
        explanations = self._explain_player_prediction(
            player, stats, is_home, team_pred, xgb,
            goal_share, shot_share, assist_share, card_share,
            team_total_goals, team_total_shots, starter_pct
        )

        return {
            "player": player.to_dict(),
            "season_stats": stats.to_dict(),
            "is_home": is_home,
            "starter_probability": round(starter_pct, 1),
            "estimated_minutes": round(avg_minutes, 0),
            "predictions": {
                "goals": round(pred_goals, 3),
                "goal_probability": round(float(goal_prob) * 100, 1),
                "shots": round(pred_shots, 2),
                "assists": round(pred_assists, 3),
                "assist_probability": round(float(assist_prob) * 100, 1),
                "key_passes": round(pred_key_passes, 2),
                "tackles": round(pred_tackles, 2),
                "interceptions": round(pred_interceptions, 2),
                "dribbles": round(pred_dribbles, 2),
                "fouls_committed": round(pred_fouls, 2),
                "yellow_card_prob": round(float(yellow_prob) * 100, 1),
                "red_card_prob": round(red_per_app * 100, 1),
                "estimated_rating": round(pred_rating, 2) if pred_rating else None,
            },
            "contribution": {
                "goal_share": round(goal_share * 100, 1),
                "shot_share": round(shot_share * 100, 1),
                "assist_share": round(assist_share * 100, 1),
                "card_share": round(card_share * 100, 1),
            },
            "team_prediction": {
                "team_lambda": round(team_lambda, 3),
                "team_shots": round(team_shots, 1),
                "team_corners": round(team_corners, 1),
                "team_cards": round(team_cards, 1),
            },
            "explanations": explanations,
        }

    def _explain_player_prediction(self, player, stats, is_home, team_pred, xgb,
                                   goal_share, shot_share, assist_share, card_share,
                                   team_total_goals, team_total_shots, starter_pct):
        """Gera explicações em linguagem natural para a predição do jogador."""
        factors = []
        apps = stats.appearances
        pos = player.position or ""
        side = "mandante" if is_home else "visitante"
        team_lambda = team_pred["lambda_home"] if is_home else team_pred["lambda_away"]

        # Método de cálculo
        factors.append({
            "type": "methodology",
            "text": (
                "A predição individual combina duas abordagens: (1) a contribuição proporcional "
                "do jogador em relação ao time na temporada, aplicada sobre a predição do time para "
                "este jogo (Dixon-Coles + XGBoost); e (2) as médias históricas do jogador por partida."
            ),
        })

        # Titular ou reserva
        if starter_pct >= 80:
            factors.append({
                "type": "positive",
                "text": f"{player.name} foi titular em {starter_pct:.0f}% dos jogos — alta probabilidade de iniciar.",
            })
        elif starter_pct >= 50:
            factors.append({
                "type": "info",
                "text": f"{player.name} foi titular em {starter_pct:.0f}% dos jogos — pode ou não iniciar.",
            })
        else:
            factors.append({
                "type": "negative",
                "text": f"{player.name} foi titular em apenas {starter_pct:.0f}% dos jogos — provavelmente entra do banco.",
            })

        # Gols
        if pos == "Attacker":
            if goal_share >= 0.15:
                factors.append({
                    "type": "positive",
                    "text": f"Responsável por {goal_share*100:.0f}% dos gols do time na temporada ({stats.goals} de {team_total_goals}). "
                            f"Com o time prevendo {team_lambda:.2f} gols, a contribuição proporcional é {team_lambda*goal_share:.3f} gols esperados.",
                })
            else:
                factors.append({
                    "type": "info",
                    "text": f"Fez {stats.goals} gols em {apps} jogos ({goal_share*100:.1f}% do total do time). "
                            f"xG individual: {team_lambda*goal_share:.3f}.",
                })
        elif stats.goals > 0:
            factors.append({
                "type": "info",
                "text": f"Mesmo sendo {pos}, marcou {stats.goals} gols na temporada ({goal_share*100:.1f}% do time). "
                        f"xG individual: {team_lambda*goal_share:.3f}.",
            })

        # Chutes
        if stats.shots_total > 0:
            shots_per_game = stats.shots_total / apps
            team_shots_match = xgb.get("home_shots", 0) if is_home else xgb.get("away_shots", 0)
            factors.append({
                "type": "info",
                "text": f"Média de {shots_per_game:.1f} chutes/jogo, representando {shot_share*100:.0f}% dos chutes do time. "
                        f"Com o time prevendo {team_shots_match:.1f} chutes, espera-se {team_shots_match*shot_share:.1f} chutes dele.",
            })

        # Assistências
        if stats.assists >= 3:
            factors.append({
                "type": "positive",
                "text": f"Forneceu {stats.assists} assistências na temporada — forte criação de jogo.",
            })

        # Cartões
        if stats.yellow_cards >= 5:
            factors.append({
                "type": "negative",
                "text": f"Acumulou {stats.yellow_cards} amarelos em {apps} jogos ({stats.yellow_cards/apps:.2f}/jogo) — jogador propenso a cartões.",
            })

        # Contexto do jogo
        factors.append({
            "type": "context",
            "text": f"O time joga como {side} — xG do time: {team_lambda:.2f} gols. "
                    f"Os modelos prevêem {xgb.get('home_shots' if is_home else 'away_shots', 0):.1f} chutes "
                    f"e {xgb.get('home_corners' if is_home else 'away_corners', 0):.1f} escanteios para o time neste jogo.",
        })

        # Rating
        if stats.rating and stats.rating >= 7.0:
            factors.append({
                "type": "positive",
                "text": f"Rating médio de {stats.rating:.2f} na temporada — desempenho acima da média.",
            })
        elif stats.rating and stats.rating < 6.5:
            factors.append({
                "type": "negative",
                "text": f"Rating médio de {stats.rating:.2f} na temporada — desempenho abaixo da média.",
            })

        return factors
