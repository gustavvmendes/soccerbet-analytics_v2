"""Rotas para análise ao vivo de partidas."""

from flask import Blueprint, jsonify, current_app
from app.services.live_monitor import get_live_monitor

live_bp = Blueprint("live", __name__)


@live_bp.route("/matches", methods=["GET"])
def get_live_matches():
    """Retorna todas as partidas ao vivo com análise completa."""
    monitor = get_live_monitor()
    data = monitor.get_live_data(current_app._get_current_object())
    return jsonify(data)


@live_bp.route("/match/<int:fixture_id>", methods=["GET"])
def get_live_match_detail(fixture_id):
    """Retorna análise detalhada de uma partida ao vivo específica."""
    monitor = get_live_monitor()
    analysis = monitor.get_match_analysis(fixture_id, current_app._get_current_object())
    if not analysis:
        return jsonify({"error": "Partida não encontrada ou não está ao vivo"}), 404
    return jsonify(analysis)


@live_bp.route("/match/<int:fixture_id>/snapshots", methods=["GET"])
def get_live_snapshots(fixture_id):
    """Retorna histórico de snapshots para análise de tendência."""
    monitor = get_live_monitor()
    snapshots = monitor.get_snapshots(fixture_id)
    return jsonify({
        "fixture_id": fixture_id,
        "snapshots": snapshots,
        "count": len(snapshots),
    })


@live_bp.route("/status", methods=["GET"])
def get_live_status():
    """Retorna status do monitor ao vivo (diagnóstico)."""
    monitor = get_live_monitor()
    return jsonify({
        "last_fetch": monitor._last_fetch,
        "cached_matches": len(monitor._cache.get("matches", [])),
        "tracked_fixtures": list(monitor._snapshots.keys()),
        "fetch_interval_seconds": monitor.FETCH_INTERVAL_SECONDS,
    })
