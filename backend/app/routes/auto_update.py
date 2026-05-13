"""Rotas para controle da atualizacao automatica de dados."""

import threading

from flask import Blueprint, jsonify, current_app
from app.services.auto_updater import get_update_status, run_incremental_update

auto_update_bp = Blueprint("auto_update", __name__)


@auto_update_bp.route("/status", methods=["GET"])
def auto_update_status():
    """Retorna status da ultima atualizacao automatica."""
    return jsonify(get_update_status())


@auto_update_bp.route("/trigger", methods=["POST"])
def auto_update_trigger():
    """Forca uma atualizacao manual via API."""
    status = get_update_status()
    if status["is_updating"]:
        return jsonify({"message": "Atualizacao ja em andamento"}), 409

    app = current_app._get_current_object()
    thread = threading.Thread(
        target=run_incremental_update,
        args=(app,),
        daemon=True,
        name="AutoUpdater-Manual",
    )
    thread.start()
    return jsonify({"message": "Atualizacao iniciada em background"})
