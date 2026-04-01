import json
import os
import joblib
from flask import current_app
from app import db
from app.models.database import Team, League, Prediction
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
