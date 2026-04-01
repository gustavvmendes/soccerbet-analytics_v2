from flask import Blueprint, jsonify, request
from app.models.database import Prediction, Team
from app.ml.predictor import Predictor

predictions_bp = Blueprint("predictions", __name__)


@predictions_bp.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body é obrigatório"}), 400

    home_team_api_id = data.get("home_team_api_id")
    away_team_api_id = data.get("away_team_api_id")

    if not home_team_api_id or not away_team_api_id:
        return jsonify({"error": "home_team_api_id e away_team_api_id são obrigatórios"}), 400

    if home_team_api_id == away_team_api_id:
        return jsonify({"error": "Os times devem ser diferentes"}), 400

    try:
        predictor = Predictor()
        result = predictor.predict(home_team_api_id, away_team_api_id)
        return jsonify(result)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Erro ao gerar predição: {str(e)}"}), 500


@predictions_bp.route("/history", methods=["GET"])
def prediction_history():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    per_page = min(per_page, 100)

    pagination = (
        Prediction.query
        .order_by(Prediction.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return jsonify({
        "predictions": [p.to_dict() for p in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
    })


@predictions_bp.route("/metrics", methods=["GET"])
def get_metrics():
    try:
        predictor = Predictor()
        metrics = predictor.get_metrics()
        return jsonify(metrics)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
