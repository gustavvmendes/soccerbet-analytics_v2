import os
import joblib
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from flask import current_app


# Features usadas pelos modelos XGBoost
FEATURE_COLS = [
    "home_as_home_avg_goals_scored", "home_as_home_avg_goals_conceded",
    "home_as_home_avg_shots", "home_as_home_avg_shots_on_target",
    "home_as_home_avg_corners", "home_as_home_avg_cards",
    "home_as_home_avg_possession", "home_as_home_win_rate",
    "home_as_home_clean_sheet_rate",
    "home_avg_goals_scored", "home_avg_goals_conceded",
    "home_avg_shots", "home_avg_shots_on_target",
    "home_avg_corners", "home_avg_cards",
    "home_avg_possession", "home_win_rate",
    "home_draw_rate", "home_loss_rate", "home_clean_sheet_rate",
    "home_goals_scored_std", "home_goals_conceded_std",
    "away_as_away_avg_goals_scored", "away_as_away_avg_goals_conceded",
    "away_as_away_avg_shots", "away_as_away_avg_shots_on_target",
    "away_as_away_avg_corners", "away_as_away_avg_cards",
    "away_as_away_avg_possession", "away_as_away_win_rate",
    "away_as_away_clean_sheet_rate",
    "away_avg_goals_scored", "away_avg_goals_conceded",
    "away_avg_shots", "away_avg_shots_on_target",
    "away_avg_corners", "away_avg_cards",
    "away_avg_possession", "away_win_rate",
    "away_draw_rate", "away_loss_rate", "away_clean_sheet_rate",
    "away_goals_scored_std", "away_goals_conceded_std",
    "h2h_home_wins", "h2h_draws", "h2h_away_wins",
    "h2h_avg_total_goals", "h2h_matches_count",
]

# Targets que o XGBoost prevê
XGBOOST_TARGETS = {
    "home_corners": "target_home_corners",
    "away_corners": "target_away_corners",
    "home_cards": "target_home_cards",
    "away_cards": "target_away_cards",
    "home_possession": "target_home_possession",
    "away_possession": "target_away_possession",
    "home_shots": "target_home_shots",
    "away_shots": "target_away_shots",
}


class XGBoostModels:
    """Gerencia os 8 modelos XGBoost para estatísticas não-Poisson."""

    def __init__(self):
        self.models = {}
        self.metrics = {}

    def train(self, df):
        """Treina todos os modelos XGBoost."""
        available_features = [c for c in FEATURE_COLS if c in df.columns]

        if len(available_features) < 10:
            raise ValueError(f"Features insuficientes: {len(available_features)}")

        X = df[available_features].fillna(0)
        weights = df["sample_weight"].values if "sample_weight" in df.columns else None

        for name, target_col in XGBOOST_TARGETS.items():
            if target_col not in df.columns:
                print(f"Aviso: target {target_col} não encontrado, pulando {name}")
                continue

            y = df[target_col].fillna(0)

            model = XGBRegressor(
                n_estimators=200,
                max_depth=4,
                learning_rate=0.05,
                min_child_weight=5,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=1.0,
                random_state=42,
                verbosity=0,
            )

            model.fit(X, y, sample_weight=weights)
            self.models[name] = model

            # Avaliar com TimeSeriesSplit
            metrics = self._evaluate(model, X, y, weights)
            self.metrics[name] = metrics
            print(f"  {name}: MAE={metrics['mae']:.3f}, RMSE={metrics['rmse']:.3f}, R²={metrics['r2']:.3f}")

        # Salvar feature names para predição
        self.feature_names = available_features

        return self

    def predict(self, features_dict):
        """Prediz todas as estatísticas para um confronto."""
        if not self.models:
            raise ValueError("Modelos não treinados")

        X = pd.DataFrame([features_dict])[self.feature_names].fillna(0)

        predictions = {}
        for name, model in self.models.items():
            pred = model.predict(X)[0]
            predictions[name] = max(0, float(pred))

        return predictions

    def save(self, directory=None):
        if directory is None:
            directory = current_app.config["ML_MODELS_DIR"]
        os.makedirs(directory, exist_ok=True)

        for name, model in self.models.items():
            path = os.path.join(directory, f"xgb_{name}.joblib")
            joblib.dump(model, path)

        meta = {"feature_names": self.feature_names, "metrics": self.metrics}
        joblib.dump(meta, os.path.join(directory, "xgb_meta.joblib"))

    def load(self, directory=None):
        if directory is None:
            directory = current_app.config["ML_MODELS_DIR"]

        meta_path = os.path.join(directory, "xgb_meta.joblib")
        if not os.path.exists(meta_path):
            raise FileNotFoundError("Modelos não encontrados. Treine primeiro.")

        meta = joblib.load(meta_path)
        self.feature_names = meta["feature_names"]
        self.metrics = meta.get("metrics", {})

        for name in XGBOOST_TARGETS:
            path = os.path.join(directory, f"xgb_{name}.joblib")
            if os.path.exists(path):
                self.models[name] = joblib.load(path)

        return self

    def _evaluate(self, model, X, y, weights):
        tscv = TimeSeriesSplit(n_splits=3)
        maes, rmses, r2s = [], [], []

        for train_idx, val_idx in tscv.split(X):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
            w_train = weights[train_idx] if weights is not None else None

            temp_model = XGBRegressor(**model.get_params())
            temp_model.fit(X_train, y_train, sample_weight=w_train)
            y_pred = temp_model.predict(X_val)

            maes.append(mean_absolute_error(y_val, y_pred))
            rmses.append(np.sqrt(mean_squared_error(y_val, y_pred)))
            r2s.append(r2_score(y_val, y_pred))

        return {
            "mae": np.mean(maes),
            "rmse": np.mean(rmses),
            "r2": np.mean(r2s),
        }

    def get_feature_importance(self, top_n=10):
        """Retorna importância das features para cada modelo."""
        importances = {}
        for name, model in self.models.items():
            imp = model.feature_importances_
            feature_imp = sorted(
                zip(self.feature_names, imp), key=lambda x: x[1], reverse=True
            )
            importances[name] = [{"feature": f, "importance": float(v)} for f, v in feature_imp[:top_n]]
        return importances
