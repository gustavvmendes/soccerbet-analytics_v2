"use client";

import { useState, useEffect, useRef } from "react";
import {
  LiveMatchesResponse,
  LiveMatchAnalysis,
  getLiveMatches,
} from "@/lib/api";
import LiveMatchDetail from "./LiveMatchDetail";
import Image from "next/image";

const POLL_INTERVAL = 15000; // 15 segundos

export default function LiveMatches() {
  const [data, setData] = useState<LiveMatchesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedFixture, setSelectedFixture] = useState<number | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchLive = async () => {
    try {
      const res = await getLiveMatches();
      setData(res.data);
    } catch {
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLive();
    intervalRef.current = setInterval(fetchLive, POLL_INTERVAL);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  if (selectedFixture !== null) {
    return (
      <LiveMatchDetail
        fixtureId={selectedFixture}
        onBack={() => setSelectedFixture(null)}
      />
    );
  }

  if (loading) {
    return (
      <div className="text-center py-20 text-[var(--text-secondary)]">
        Carregando partidas ao vivo...
      </div>
    );
  }

  const matches = data?.matches ?? [];

  if (matches.length === 0) {
    return (
      <div className="text-center py-20">
        <div className="text-5xl mb-4">⚽</div>
        <h3 className="text-xl font-semibold mb-2">
          Nenhuma partida ao vivo no momento
        </h3>
        <p className="text-[var(--text-secondary)]">
          As partidas do Brasileirão Série A aparecerão aqui quando estiverem em
          andamento.
        </p>
        {data?.last_updated && (
          <p className="text-xs text-[var(--text-secondary)] mt-4">
            Última verificação:{" "}
            {new Date(data.last_updated).toLocaleTimeString("pt-BR")}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
          </span>
          <h2 className="text-lg font-semibold">
            {matches.length} partida{matches.length !== 1 ? "s" : ""} ao vivo
          </h2>
        </div>
        {data?.last_updated && (
          <span className="text-xs text-[var(--text-secondary)]">
            Atualizado:{" "}
            {new Date(data.last_updated).toLocaleTimeString("pt-BR")}
          </span>
        )}
      </div>

      {/* Cards de partidas */}
      <div className="grid gap-4">
        {matches.map((match) => (
          <LiveMatchCard
            key={match.fixture_id}
            match={match}
            onClick={() => setSelectedFixture(match.fixture_id)}
          />
        ))}
      </div>
    </div>
  );
}

function LiveMatchCard({
  match,
  onClick,
}: {
  match: LiveMatchAnalysis;
  onClick: () => void;
}) {
  const lp = match.live_probabilities;
  const statusLabel = getStatusLabel(match.status, match.elapsed);

  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)] hover:border-[var(--accent-blue)] transition-colors"
    >
      {/* Status / Minuto */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
          </span>
          <span className="text-xs font-semibold text-red-400 uppercase">
            {statusLabel}
          </span>
        </div>
        <span className="text-xs text-[var(--text-secondary)]">
          {match.elapsed}&apos;
        </span>
      </div>

      {/* Placar */}
      <div className="grid grid-cols-[1fr_auto_1fr] gap-4 items-center mb-4">
        <div className="flex items-center gap-3">
          {match.home_team.logo && (
            <Image
              src={match.home_team.logo}
              alt={match.home_team.name}
              width={36}
              height={36}
              className="object-contain"
            />
          )}
          <span className="font-semibold text-sm truncate">
            {match.home_team.name}
          </span>
        </div>
        <div className="text-center">
          <span className="text-3xl font-bold tabular-nums">
            {match.score.home} - {match.score.away}
          </span>
        </div>
        <div className="flex items-center gap-3 justify-end">
          <span className="font-semibold text-sm truncate text-right">
            {match.away_team.name}
          </span>
          {match.away_team.logo && (
            <Image
              src={match.away_team.logo}
              alt={match.away_team.name}
              width={36}
              height={36}
              className="object-contain"
            />
          )}
        </div>
      </div>

      {/* Barra de probabilidade */}
      <div className="mb-3">
        <div className="flex h-3 rounded-full overflow-hidden">
          <div
            className="bg-[var(--accent-blue)] transition-all duration-700"
            style={{ width: `${lp.home_win_prob * 100}%` }}
          />
          <div
            className="bg-gray-500 transition-all duration-700"
            style={{ width: `${lp.draw_prob * 100}%` }}
          />
          <div
            className="bg-[var(--accent-red)] transition-all duration-700"
            style={{ width: `${lp.away_win_prob * 100}%` }}
          />
        </div>
        <div className="flex justify-between text-xs mt-1 text-[var(--text-secondary)]">
          <span>{(lp.home_win_prob * 100).toFixed(0)}%</span>
          <span>{(lp.draw_prob * 100).toFixed(0)}%</span>
          <span>{(lp.away_win_prob * 100).toFixed(0)}%</span>
        </div>
      </div>

      {/* xG + Over/Under resumo */}
      <div className="grid grid-cols-3 gap-3 text-center">
        <div className="bg-[var(--bg-secondary)] rounded-lg p-2">
          <div className="text-xs text-[var(--text-secondary)]">xG</div>
          <div className="text-sm font-semibold">
            {lp.home_xg} - {lp.away_xg}
          </div>
        </div>
        <div className="bg-[var(--bg-secondary)] rounded-lg p-2">
          <div className="text-xs text-[var(--text-secondary)]">Over 2.5</div>
          <div className="text-sm font-semibold">
            {(lp.over_under.over_2_5 * 100).toFixed(0)}%
          </div>
        </div>
        <div className="bg-[var(--bg-secondary)] rounded-lg p-2">
          <div className="text-xs text-[var(--text-secondary)]">Próx. Gol</div>
          <div className="text-sm font-semibold">
            {lp.next_goal.no_more_goals > 0.5 ? (
              <span className="text-gray-400">Nenhum</span>
            ) : lp.next_goal.home > lp.next_goal.away ? (
              <span className="text-blue-400">Casa</span>
            ) : (
              <span className="text-red-400">Fora</span>
            )}
          </div>
        </div>
      </div>

      {/* Insights rápidos */}
      {match.insights.length > 0 && (
        <div className="mt-3 pt-3 border-t border-[var(--border-color)]">
          <p className="text-xs text-[var(--text-secondary)] truncate">
            {match.insights[0].text}
          </p>
        </div>
      )}
    </button>
  );
}

function getStatusLabel(status: string, elapsed: number): string {
  switch (status) {
    case "1H":
      return `1º Tempo ${elapsed}'`;
    case "2H":
      return `2º Tempo ${elapsed}'`;
    case "HT":
      return "Intervalo";
    case "ET":
      return "Prorrogação";
    case "BT":
      return "Intervalo Prorrogação";
    case "P":
      return "Pênaltis";
    case "SUSP":
      return "Suspenso";
    case "INT":
      return "Interrompido";
    default:
      return `Ao Vivo ${elapsed}'`;
  }
}
