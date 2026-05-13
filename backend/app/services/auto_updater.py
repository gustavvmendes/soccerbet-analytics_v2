"""
Servico de atualizacao automatica de dados.

- Ao iniciar o Flask, roda uma atualizacao incremental em background.
- Opcionalmente, agenda atualizacoes periodicas (a cada N horas).
"""

import threading
import time
import traceback
from datetime import datetime

# Controle de estado
_update_status = {
    "last_update": None,
    "last_update_result": None,
    "is_updating": False,
    "history": [],
}
_status_lock = threading.Lock()
_scheduler_thread = None


def get_update_status():
    """Retorna status da ultima atualizacao."""
    with _status_lock:
        return dict(_update_status)


def _log_update(message, success=True):
    """Registra resultado de uma atualizacao."""
    with _status_lock:
        _update_status["last_update"] = datetime.now().isoformat()
        _update_status["last_update_result"] = message
        _update_status["is_updating"] = False
        _update_status["history"].append({
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "success": success,
        })
        # Manter apenas ultimos 20 registros
        _update_status["history"] = _update_status["history"][-20:]


def _get_seasons_to_update(app):
    """
    Detecta quais temporadas atualizar.
    1. Pega as temporadas ja existentes no banco
    2. Se nenhuma existir, usa a configuracao CURRENT_SEASON do config (ou padrao)
    """
    with app.app_context():
        from app.models.database import Season
        seasons_in_db = [s.year for s in Season.query.order_by(Season.year).all()]

    if seasons_in_db:
        return seasons_in_db
    else:
        # Temporada padrao - ajuste conforme seu plano da API
        default = app.config.get("CURRENT_SEASON", 2024)
        return [default]


def run_incremental_update(app):
    """
    Atualizacao incremental: coleta apenas dados novos/atualizados.

    1. Partidas finalizadas recentes (que ainda nao estao no banco) + stats
    2. Atualizar status de partidas que eram "NS" e agora estao "FT"
    3. Jogos futuros (novos ou atualizados)
    4. Odds para jogos futuros
    5. Lesoes para jogos futuros
    """
    with _status_lock:
        if _update_status["is_updating"]:
            print("[AutoUpdater] Atualizacao ja em andamento, ignorando...")
            return
        _update_status["is_updating"] = True

    print("")
    print("=" * 60)
    print("[AutoUpdater] Iniciando atualizacao incremental...")
    print("[AutoUpdater] Horario: %s" % datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    print("=" * 60)

    try:
        seasons = _get_seasons_to_update(app)
        print("[AutoUpdater] Temporadas a atualizar: %s" % seasons)

        total_summary = {
            "new_matches": 0,
            "updated_matches": 0,
            "upcoming_fixtures": 0,
            "odds_collected": 0,
            "injuries_collected": 0,
        }

        for season in seasons:
            print("")
            print("[AutoUpdater] --- Temporada %d ---" % season)
            season_summary = _update_season(app, season)
            for key in total_summary:
                total_summary[key] += season_summary.get(key, 0)

        # Resumo final
        msg = (
            "Atualizacao concluida: "
            "%d novas, %d atualizadas, %d futuros, %d odds, %d lesoes"
            % (
                total_summary["new_matches"],
                total_summary["updated_matches"],
                total_summary["upcoming_fixtures"],
                total_summary["odds_collected"],
                total_summary["injuries_collected"],
            )
        )
        print("")
        print("[AutoUpdater] OK - %s" % msg)
        print("=" * 60)
        print("")
        _log_update(msg, success=True)

    except Exception as e:
        error_msg = "Erro na atualizacao: %s" % str(e)
        print("[AutoUpdater] ERRO - %s" % error_msg)
        traceback.print_exc()
        _log_update(error_msg, success=False)


def _update_season(app, season):
    """Atualiza dados de uma temporada especifica."""
    summary = {
        "new_matches": 0,
        "updated_matches": 0,
        "upcoming_fixtures": 0,
        "odds_collected": 0,
        "injuries_collected": 0,
    }

    with app.app_context():
        from app.services.api_football import APIFootballService
        from app.services.data_processor import DataProcessor
        from app.models.database import Match, MatchStatistics, MatchOdds, MatchInjury
        from app import db

        # Garantir sessao limpa para evitar "database is locked"
        try:
            db.session.rollback()
        except Exception:
            pass

        api = APIFootballService()
        processor = DataProcessor()

        league_api_id = app.config["BRASILEIRAO_LEAGUE_ID"]
        processor.ensure_league(league_api_id)
        db.session.commit()  # Commit cedo para liberar lock

        # --- 1. Buscar todas as partidas da temporada ---
        print("[AutoUpdater] Buscando partidas da API (season=%d)..." % season)
        try:
            all_fixtures = api.get_fixtures(season)
        except Exception as e:
            print("[AutoUpdater] Erro ao buscar fixtures da temporada %d: %s" % (season, e))
            return summary

        print("[AutoUpdater] Total de partidas na API: %d" % len(all_fixtures))

        # --- 2. Processar partidas finalizadas que nao estao no banco ---
        finished = [f for f in all_fixtures if f["fixture"]["status"]["short"] == "FT"]
        existing_api_ids = set(
            row[0] for row in db.session.query(Match.api_id)
            .filter(Match.status == "FT").all()
        )

        new_finished = [
            f for f in finished
            if f["fixture"]["id"] not in existing_api_ids
        ]

        if new_finished:
            print("[AutoUpdater] %d partida(s) nova(s) finalizada(s) encontrada(s)" % len(new_finished))
            for i, fixture in enumerate(new_finished):
                fixture_id = fixture["fixture"]["id"]
                try:
                    stats = api.get_fixture_statistics(fixture_id)
                    fixture["statistics"] = stats
                    time.sleep(0.35)
                except Exception as e:
                    print("[AutoUpdater] Erro ao buscar stats do fixture %d: %s" % (fixture_id, e))

            processed = processor.process_season_data(new_finished, league_api_id, season)
            summary["new_matches"] = processed
            print("[AutoUpdater] OK - %d partida(s) nova(s) processada(s)" % processed)
        else:
            print("[AutoUpdater] OK - Nenhuma partida nova finalizada")

        # --- 3. Sincronizar TODAS as partidas existentes no banco ---
        # Atualiza status, placar, data (reagendamentos), etc.
        all_db_api_ids = set(
            row[0] for row in db.session.query(Match.api_id).all()
        )

        # Criar lookup rapido: api_id -> fixture data
        api_fixture_map = {f["fixture"]["id"]: f for f in all_fixtures}

        # Partidas no banco que precisam ser verificadas (nao-finalizadas)
        non_final_matches = (
            db.session.query(Match)
            .filter(Match.status.in_(["NS", "TBD", "PST", "SUSP"]))
            .all()
        )

        updated_count = 0
        for match in non_final_matches:
            api_data = api_fixture_map.get(match.api_id)
            if not api_data:
                continue

            new_status = api_data["fixture"]["status"]["short"]
            goals = api_data["goals"]
            score = api_data.get("score", {})
            ht = score.get("halftime", {})

            # Verificar se mudou algo
            date_str = api_data["fixture"]["date"]
            if date_str.endswith("Z"):
                date_str = date_str.replace("Z", "+00:00")

            from datetime import datetime as dt
            try:
                new_date = dt.fromisoformat(date_str)
                # Remover timezone para comparar com datetime naive do banco
                new_date = new_date.replace(tzinfo=None)
            except Exception:
                new_date = match.date

            new_round = api_data.get("league", {}).get("round")
            changed = (
                match.status != new_status
                or match.home_goals != goals.get("home")
                or match.away_goals != goals.get("away")
                or (match.date and new_date and abs((match.date - new_date).total_seconds()) > 60)
            )

            if not changed:
                continue

            try:
                with db.session.no_autoflush:
                    match.status = new_status
                    match.home_goals = goals.get("home")
                    match.away_goals = goals.get("away")
                    match.home_goals_ht = ht.get("home")
                    match.away_goals_ht = ht.get("away")
                    match.date = new_date
                    if new_round:
                        match.round = new_round

                    # Se agora esta FT, buscar estatisticas
                    if new_status == "FT":
                        try:
                            stats = api.get_fixture_statistics(match.api_id)
                            if stats and len(stats) >= 2:
                                existing_stats = MatchStatistics.query.filter_by(match_id=match.id).first()
                                if not existing_stats:
                                    home_stats = stats[0].get("statistics", [])
                                    away_stats = stats[1].get("statistics", [])
                                    match_stats = MatchStatistics(
                                        match_id=match.id,
                                        home_possession=processor._parse_stat(home_stats, "Ball Possession"),
                                        away_possession=processor._parse_stat(away_stats, "Ball Possession"),
                                        home_shots_total=processor._parse_stat(home_stats, "Total Shots"),
                                        away_shots_total=processor._parse_stat(away_stats, "Total Shots"),
                                        home_shots_on_target=processor._parse_stat(home_stats, "Shots on Goal"),
                                        away_shots_on_target=processor._parse_stat(away_stats, "Shots on Goal"),
                                        home_corners=processor._parse_stat(home_stats, "Corner Kicks"),
                                        away_corners=processor._parse_stat(away_stats, "Corner Kicks"),
                                        home_yellow_cards=processor._parse_stat(home_stats, "Yellow Cards"),
                                        away_yellow_cards=processor._parse_stat(away_stats, "Yellow Cards"),
                                        home_red_cards=processor._parse_stat(home_stats, "Red Cards"),
                                        away_red_cards=processor._parse_stat(away_stats, "Red Cards"),
                                        home_fouls=processor._parse_stat(home_stats, "Fouls"),
                                        away_fouls=processor._parse_stat(away_stats, "Fouls"),
                                        home_offsides=processor._parse_stat(home_stats, "Offsides"),
                                        away_offsides=processor._parse_stat(away_stats, "Offsides"),
                                        home_passes_total=processor._parse_stat(home_stats, "Total passes"),
                                        away_passes_total=processor._parse_stat(away_stats, "Total passes"),
                                        home_passes_accurate=processor._parse_stat(home_stats, "Passes accurate"),
                                        away_passes_accurate=processor._parse_stat(away_stats, "Passes accurate"),
                                    )
                                    db.session.add(match_stats)
                            time.sleep(0.35)
                        except Exception as e:
                            print("[AutoUpdater] Erro ao buscar stats do fixture %d: %s" % (match.api_id, e))

                db.session.commit()
                updated_count += 1
            except Exception as e:
                print("[AutoUpdater] Erro ao sincronizar fixture %d: %s" % (match.api_id, e))
                try:
                    db.session.rollback()
                except Exception:
                    pass

        if updated_count:
            print("[AutoUpdater] OK - %d partida(s) sincronizada(s)" % updated_count)
        summary["updated_matches"] = updated_count

        # --- 4. Processar jogos futuros novos ---
        upcoming = [
            f for f in all_fixtures
            if f["fixture"]["status"]["short"] in {"NS", "TBD", "PST", "SUSP"}
        ]
        upcoming_processed = processor.process_upcoming_fixtures(upcoming, league_api_id, season)
        summary["upcoming_fixtures"] = upcoming_processed
        print("[AutoUpdater] OK - %d jogo(s) futuro(s) novo(s)" % upcoming_processed)

        # --- 5. Odds para jogos futuros (so os que nao tem odds ainda) ---
        upcoming_ns = [
            f for f in all_fixtures
            if f["fixture"]["status"]["short"] in {"NS", "TBD"}
        ]
        odds_count = 0
        for fixture in upcoming_ns:
            fixture_id = fixture["fixture"]["id"]
            existing_odds = MatchOdds.query.filter_by(match_api_id=fixture_id).first()
            if not existing_odds:
                try:
                    odds = api.get_odds(fixture_id)
                    if odds:
                        processor.process_odds([{"fixture_id": fixture_id, "odds": odds}])
                        odds_count += 1
                    time.sleep(0.35)
                except Exception as e:
                    print("[AutoUpdater] Erro ao buscar odds do fixture %d: %s" % (fixture_id, e))
        summary["odds_collected"] = odds_count
        if odds_count:
            print("[AutoUpdater] OK - %d odd(s) coletada(s)" % odds_count)

        # --- 6. Lesoes para jogos futuros (so os que nao tem) ---
        injuries_count = 0
        for fixture in upcoming_ns:
            fixture_id = fixture["fixture"]["id"]
            existing_injuries = MatchInjury.query.filter_by(match_api_id=fixture_id).first()
            if not existing_injuries:
                try:
                    injuries = api.get_injuries(fixture_id=fixture_id)
                    if injuries:
                        processor.process_injuries([{"fixture_id": fixture_id, "injuries": injuries}])
                        injuries_count += 1
                    time.sleep(0.35)
                except Exception as e:
                    print("[AutoUpdater] Erro ao buscar injuries do fixture %d: %s" % (fixture_id, e))
        summary["injuries_collected"] = injuries_count
        if injuries_count:
            print("[AutoUpdater] OK - %d lesao(oes) coletada(s)" % injuries_count)

    return summary


def start_startup_update(app):
    """Inicia atualizacao ao iniciar o servidor (em background thread)."""
    if not app.config.get("API_FOOTBALL_KEY"):
        print("[AutoUpdater] AVISO: API_FOOTBALL_KEY nao configurada, pulando atualizacao automatica")
        return

    print("[AutoUpdater] Agendando atualizacao inicial em 3 segundos...")

    def delayed_update():
        time.sleep(3)  # Esperar o servidor ficar pronto
        run_incremental_update(app)

    thread = threading.Thread(target=delayed_update, daemon=True, name="AutoUpdater-Startup")
    thread.start()


def start_periodic_updates(app, interval_hours=6):
    """
    Inicia thread de atualizacao periodica.
    Roda a cada `interval_hours` horas.
    """
    global _scheduler_thread

    if not app.config.get("API_FOOTBALL_KEY"):
        return

    if _scheduler_thread and _scheduler_thread.is_alive():
        print("[AutoUpdater] Scheduler ja esta rodando")
        return

    interval_seconds = interval_hours * 3600

    def scheduler_loop():
        print("[AutoUpdater] Scheduler iniciado: atualizacao a cada %dh" % interval_hours)
        while True:
            time.sleep(interval_seconds)
            print("")
            print("[AutoUpdater] Atualizacao periodica (%dh)..." % interval_hours)
            run_incremental_update(app)

    _scheduler_thread = threading.Thread(
        target=scheduler_loop, daemon=True, name="AutoUpdater-Scheduler"
    )
    _scheduler_thread.start()
