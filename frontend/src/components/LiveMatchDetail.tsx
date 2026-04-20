"use client";

import { useState, useEffect, useRef } from "react";
import {
  LiveMatchAnalysis,
  LiveEvent,
  getLiveMatchDetail,
} from "@/lib/api";
import Image from "next/image";

const POLL_INTERVAL = 15000;

interface Props {
  fixtureId: number;
  onBack: () => void;
}

export default function LiveMatchDetail({ fixtureId, onBack }: Props) {
  const [match, setMatch] = useState<LiveMatchAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchDetail = async () => {
    try {
      const res = await getLiveMatchDetail(fixtureId);
      setMatch(res.data);
    } catch {
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
    intervalRef.current = setInterval(fetchDetail, POLL_INTERVAL);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fixtureId]);

  if (loading || !match) {
    return (
      <div className="text-center py-20 text-[var(--text-secondary)]">
        Carregando dados ao vivo...
      </div>
    );
  }

  const lp = match.live_probabilities;
  const stats = match.statistics;
  const mom = match.momentum;

  return (
    <div className="space-y-6">
      {/* Header com voltar */}
      <button
        onClick={onBack}
        className="text-sm text-[var(--accent-blue)] hover:underline"
      >
        ← Voltar às partidas ao vivo
      </button>

      {/* Placar principal */}
      <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)]">
        <div className="flex items-center justify-center gap-2 mb-4">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
          </span>
          <span className="text-sm font-semibold text-red-400">
            {getStatusLabel(match.status, match.elapsed)}
          </span>
        </div>

        <div className="grid grid-cols-[1fr_auto_1fr] gap-6 items-center">
          <div className="flex flex-col items-center gap-2">
            {match.home_team.logo && (
              <Image
                src={match.home_team.logo}
                alt={match.home_team.name}
                width={64}
                height={64}
                className="object-contain"
              />
            )}
            <span className="font-bold text-lg text-center">
              {match.home_team.name}
            </span>
            {lp.modifiers.home_red_cards > 0 && (
              <span className="text-xs bg-red-600 text-white px-2 py-0.5 rounded">
                {lp.modifiers.home_red_cards} expulsão
              </span>
            )}
          </div>
          <div className="text-center">
            <div className="text-5xl font-bold tabular-nums">
              {match.score.home} - {match.score.away}
            </div>
            {match.score.halftime.home !== null && (
              <div className="text-xs text-[var(--text-secondary)] mt-1">
                HT: {match.score.halftime.home} - {match.score.halftime.away}
              </div>
            )}
          </div>
          <div className="flex flex-col items-center gap-2">
            {match.away_team.logo && (
              <Image
                src={match.away_team.logo}
                alt={match.away_team.name}
                width={64}
                height={64}
                className="object-contain"
              />
            )}
            <span className="font-bold text-lg text-center">
              {match.away_team.name}
            </span>
            {lp.modifiers.away_red_cards > 0 && (
              <span className="text-xs bg-red-600 text-white px-2 py-0.5 rounded">
                {lp.modifiers.away_red_cards} expulsão
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Probabilidades ao vivo */}
      <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)]">
        <h3 className="text-lg font-semibold mb-4">
          Probabilidades ao Vivo
        </h3>

        {/* Barra principal */}
        <div className="mb-4">
          <div className="flex h-5 rounded-full overflow-hidden text-xs font-bold">
            <div
              className="bg-[var(--accent-blue)] flex items-center justify-center text-white transition-all duration-700"
              style={{ width: `${lp.home_win_prob * 100}%` }}
            >
              {lp.home_win_prob > 0.08 &&
                `${(lp.home_win_prob * 100).toFixed(0)}%`}
            </div>
            <div
              className="bg-gray-500 flex items-center justify-center text-white transition-all duration-700"
              style={{ width: `${lp.draw_prob * 100}%` }}
            >
              {lp.draw_prob > 0.08 &&
                `${(lp.draw_prob * 100).toFixed(0)}%`}
            </div>
            <div
              className="bg-[var(--accent-red)] flex items-center justify-center text-white transition-all duration-700"
              style={{ width: `${lp.away_win_prob * 100}%` }}
            >
              {lp.away_win_prob > 0.08 &&
                `${(lp.away_win_prob * 100).toFixed(0)}%`}
            </div>
          </div>
          <div className="flex justify-between text-xs text-[var(--text-secondary)] mt-1">
            <span>Casa</span>
            <span>Empate</span>
            <span>Fora</span>
          </div>
        </div>

        {/* Comparação pré-jogo vs ao vivo */}
        {match.pre_match_probabilities.home_win !== null && (
          <div className="grid grid-cols-3 gap-3 text-center text-sm mb-4">
            <ProbShift
              label="Casa"
              pre={match.pre_match_probabilities.home_win ?? 0}
              live={lp.home_win_prob}
            />
            <ProbShift
              label="Empate"
              pre={match.pre_match_probabilities.draw ?? 0}
              live={lp.draw_prob}
            />
            <ProbShift
              label="Fora"
              pre={match.pre_match_probabilities.away_win ?? 0}
              live={lp.away_win_prob}
            />
          </div>
        )}

        {/* Placar mais provável */}
        <div className="text-center bg-[var(--bg-secondary)] rounded-lg p-3">
          <span className="text-xs text-[var(--text-secondary)]">
            Placar mais provável:
          </span>
          <span className="ml-2 font-bold">
            {lp.most_likely_final_score.home} - {lp.most_likely_final_score.away}
          </span>
        </div>
      </div>

      {/* xG + Estatísticas */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* xG */}
        <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)]">
          <h3 className="text-lg font-semibold mb-4">Expected Goals (xG)</h3>
          <div className="grid grid-cols-[1fr_auto_1fr] gap-4 items-center text-center">
            <div>
              <div className="text-3xl font-bold text-blue-400">
                {lp.home_xg}
              </div>
              <div className="text-xs text-[var(--text-secondary)]">
                {match.home_team.name}
              </div>
            </div>
            <div className="text-sm text-[var(--text-secondary)]">xG</div>
            <div>
              <div className="text-3xl font-bold text-red-400">
                {lp.away_xg}
              </div>
              <div className="text-xs text-[var(--text-secondary)]">
                {match.away_team.name}
              </div>
            </div>
          </div>
          <div className="mt-3 text-xs text-center text-[var(--text-secondary)]">
            Gols reais: {match.score.home} - {match.score.away}
          </div>
        </div>

        {/* Próximo gol */}
        <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)]">
          <h3 className="text-lg font-semibold mb-4">Próximo Gol</h3>
          <div className="space-y-3">
            <BarRow
              label={match.home_team.name}
              value={lp.next_goal.home}
              color="var(--accent-blue)"
            />
            <BarRow
              label={match.away_team.name}
              value={lp.next_goal.away}
              color="var(--accent-red)"
            />
            <BarRow
              label="Nenhum gol"
              value={lp.next_goal.no_more_goals}
              color="#6b7280"
            />
          </div>
        </div>
      </div>

      {/* Over/Under + BTTS */}
      <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)]">
        <h3 className="text-lg font-semibold mb-4">Over/Under & BTTS</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {Object.entries(lp.over_under).map(([key, val]) => {
            const label = key.replace("over_", "Over ").replace("_", ".");
            return (
              <div
                key={key}
                className="bg-[var(--bg-secondary)] rounded-lg p-3 text-center"
              >
                <div className="text-xs text-[var(--text-secondary)]">
                  {label}
                </div>
                <div className="text-lg font-bold">
                  {(val * 100).toFixed(0)}%
                </div>
              </div>
            );
          })}
          <div className="bg-[var(--bg-secondary)] rounded-lg p-3 text-center">
            <div className="text-xs text-[var(--text-secondary)]">
              Ambos Marcam
            </div>
            <div className="text-lg font-bold">
              {(lp.btts_prob * 100).toFixed(0)}%
            </div>
          </div>
        </div>
      </div>

      {/* Momentum */}
      <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)]">
        <h3 className="text-lg font-semibold mb-4">Momentum</h3>
        <div className="mb-3">
          <div className="flex h-4 rounded-full overflow-hidden">
            <div
              className="bg-[var(--accent-blue)] transition-all duration-700"
              style={{ width: `${mom.home}%` }}
            />
            <div
              className="bg-[var(--accent-red)] transition-all duration-700"
              style={{ width: `${mom.away}%` }}
            />
          </div>
          <div className="flex justify-between text-xs mt-1 text-[var(--text-secondary)]">
            <span>
              {match.home_team.name} ({mom.home}%)
            </span>
            <span>
              {match.away_team.name} ({mom.away}%)
            </span>
          </div>
        </div>
        <div className="text-center text-sm">
          {mom.trend === "home_pressing" && (
            <span className="text-blue-400">
              📈 {match.home_team.name} pressionando
            </span>
          )}
          {mom.trend === "away_pressing" && (
            <span className="text-red-400">
              📈 {match.away_team.name} pressionando
            </span>
          )}
          {mom.trend === "stable" && (
            <span className="text-gray-400">Jogo equilibrado</span>
          )}
        </div>
      </div>

      {/* Estatísticas ao vivo */}
      <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)]">
        <h3 className="text-lg font-semibold mb-4">Estatísticas ao Vivo</h3>
        <div className="space-y-3">
          <StatBar
            label="Posse de Bola"
            home={stats.home_possession ?? 50}
            away={stats.away_possession ?? 50}
            suffix="%"
          />
          <StatBar
            label="Finalizações"
            home={stats.home_shots_total ?? 0}
            away={stats.away_shots_total ?? 0}
          />
          <StatBar
            label="No Gol"
            home={stats.home_shots_on_target ?? 0}
            away={stats.away_shots_on_target ?? 0}
          />
          <StatBar
            label="Escanteios"
            home={stats.home_corners ?? 0}
            away={stats.away_corners ?? 0}
          />
          <StatBar
            label="Faltas"
            home={stats.home_fouls ?? 0}
            away={stats.away_fouls ?? 0}
          />
          <StatBar
            label="Impedimentos"
            home={stats.home_offsides ?? 0}
            away={stats.away_offsides ?? 0}
          />
          <StatBar
            label="Cartões Amarelos"
            home={stats.home_yellow_cards ?? 0}
            away={stats.away_yellow_cards ?? 0}
          />
        </div>
      </div>

      {/* Insights */}
      {match.insights.length > 0 && (
        <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)]">
          <h3 className="text-lg font-semibold mb-4">Análise do Modelo</h3>
          <div className="space-y-2">
            {match.insights.map((insight, i) => (
              <div
                key={i}
                className={`p-3 rounded-lg text-sm ${
                  insight.severity === "critical"
                    ? "bg-red-900/20 border border-red-800/40 text-red-300"
                    : insight.severity === "high"
                    ? "bg-yellow-900/20 border border-yellow-800/40 text-yellow-300"
                    : insight.severity === "medium"
                    ? "bg-blue-900/20 border border-blue-800/40 text-blue-300"
                    : "bg-[var(--bg-secondary)] text-[var(--text-secondary)]"
                }`}
              >
                {insight.text}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Eventos / Timeline */}
      {match.events.length > 0 && (
        <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)]">
          <h3 className="text-lg font-semibold mb-4">Eventos</h3>
          <div className="space-y-2">
            {match.events.map((event, i) => (
              <EventRow
                key={i}
                event={event}
                homeTeamId={match.home_team.api_id}
              />
            ))}
          </div>
        </div>
      )}

      {/* Modificadores do modelo */}
      <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)]">
        <h3 className="text-sm font-semibold mb-3 text-[var(--text-secondary)]">
          Parâmetros do Modelo
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center text-xs">
          <div className="bg-[var(--bg-secondary)] rounded-lg p-2">
            <div className="text-[var(--text-secondary)]">λ Casa Rest.</div>
            <div className="font-bold">
              {lp.lambda_home_remaining}
            </div>
          </div>
          <div className="bg-[var(--bg-secondary)] rounded-lg p-2">
            <div className="text-[var(--text-secondary)]">λ Fora Rest.</div>
            <div className="font-bold">
              {lp.lambda_away_remaining}
            </div>
          </div>
          <div className="bg-[var(--bg-secondary)] rounded-lg p-2">
            <div className="text-[var(--text-secondary)]">Perf. Casa</div>
            <div className="font-bold">
              {(lp.modifiers.home_performance * 100).toFixed(0)}%
            </div>
          </div>
          <div className="bg-[var(--bg-secondary)] rounded-lg p-2">
            <div className="text-[var(--text-secondary)]">Perf. Fora</div>
            <div className="font-bold">
              {(lp.modifiers.away_performance * 100).toFixed(0)}%
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Componentes auxiliares ── */

function ProbShift({
  label,
  pre,
  live,
}: {
  label: string;
  pre: number;
  live: number;
}) {
  const diff = (live - pre) * 100;
  const arrow = diff > 1 ? "↑" : diff < -1 ? "↓" : "→";
  const color =
    diff > 3
      ? "text-green-400"
      : diff < -3
      ? "text-red-400"
      : "text-[var(--text-secondary)]";

  return (
    <div className="bg-[var(--bg-secondary)] rounded-lg p-2">
      <div className="text-xs text-[var(--text-secondary)]">{label}</div>
      <div className="font-bold">{(live * 100).toFixed(0)}%</div>
      <div className={`text-xs ${color}`}>
        {arrow} {diff >= 0 ? "+" : ""}
        {diff.toFixed(0)}pp
      </div>
    </div>
  );
}

function BarRow({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span>{label}</span>
        <span className="font-semibold">{(value * 100).toFixed(0)}%</span>
      </div>
      <div className="h-2 bg-[var(--bg-primary)] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${value * 100}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

function StatBar({
  label,
  home,
  away,
  suffix = "",
}: {
  label: string;
  home: number;
  away: number;
  suffix?: string;
}) {
  const total = home + away || 1;
  const hPct = (home / total) * 100;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="font-medium">
          {typeof home === "number" && !Number.isInteger(home)
            ? home.toFixed(1)
            : home}
          {suffix}
        </span>
        <span className="text-[var(--text-secondary)]">{label}</span>
        <span className="font-medium">
          {typeof away === "number" && !Number.isInteger(away)
            ? away.toFixed(1)
            : away}
          {suffix}
        </span>
      </div>
      <div className="flex h-2 rounded-full overflow-hidden bg-[var(--bg-primary)]">
        <div
          className="bg-[var(--accent-blue)] transition-all duration-500"
          style={{ width: `${hPct}%` }}
        />
        <div
          className="bg-[var(--accent-red)] transition-all duration-500"
          style={{ width: `${100 - hPct}%` }}
        />
      </div>
    </div>
  );
}

function EventRow({
  event,
  homeTeamId,
}: {
  event: LiveEvent;
  homeTeamId: number;
}) {
  const isHome = event.team_id === homeTeamId;
  const icon = getEventIcon(event.type, event.detail);

  return (
    <div
      className={`flex items-center gap-3 text-sm ${
        isHome ? "" : "flex-row-reverse text-right"
      }`}
    >
      <span className="text-xs font-mono text-[var(--text-secondary)] w-8 shrink-0 text-center">
        {event.time_elapsed}&apos;
        {event.time_extra ? `+${event.time_extra}` : ""}
      </span>
      <span className="text-lg shrink-0">{icon}</span>
      <div className="min-w-0">
        <span className="font-medium">{event.player_name}</span>
        {event.assist_name && (
          <span className="text-[var(--text-secondary)]">
            {" "}
            ({event.assist_name})
          </span>
        )}
        {event.detail && event.type !== "Goal" && (
          <span className="text-xs text-[var(--text-secondary)] ml-1">
            {event.detail}
          </span>
        )}
      </div>
    </div>
  );
}

function getEventIcon(type: string, detail: string): string {
  switch (type) {
    case "Goal":
      return detail === "Own Goal" ? "🔴⚽" : "⚽";
    case "Card":
      return detail === "Red Card"
        ? "🟥"
        : detail === "Second Yellow card"
        ? "🟨🟥"
        : "🟨";
    case "subst":
      return "🔄";
    case "Var":
      return "📺";
    default:
      return "•";
  }
}

function getStatusLabel(status: string, elapsed: number): string {
  switch (status) {
    case "1H":
      return `1º Tempo — ${elapsed}'`;
    case "2H":
      return `2º Tempo — ${elapsed}'`;
    case "HT":
      return "Intervalo";
    case "ET":
      return `Prorrogação — ${elapsed}'`;
    case "BT":
      return "Intervalo da Prorrogação";
    case "P":
      return "Pênaltis";
    case "SUSP":
      return "Jogo Suspenso";
    case "INT":
      return "Jogo Interrompido";
    default:
      return `Ao Vivo — ${elapsed}'`;
  }
}
