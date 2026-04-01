"use client";

import { useState } from "react";
import { Team, MatchData, getMatchHistory } from "@/lib/api";
import Image from "next/image";
import MatchDetails from "./MatchDetails";

interface Props {
  teams: Team[];
}

export default function MatchHistory({ teams }: Props) {
  const [matches, setMatches] = useState<MatchData[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [selectedTeam, setSelectedTeam] = useState<number | undefined>();
  const [selectedSeason, setSelectedSeason] = useState<number | undefined>();
  const [selectedMatchId, setSelectedMatchId] = useState<number | null>(null);

  const fetchMatches = async (p: number = 1) => {
    setLoading(true);
    try {
      const res = await getMatchHistory({
        page: p,
        per_page: 15,
        team_id: selectedTeam,
        season: selectedSeason,
      });
      setMatches(res.data.matches);
      setPage(res.data.page);
      setTotalPages(res.data.pages);
    } catch {
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    fetchMatches(1);
  };

  // Se uma partida foi selecionada, mostrar os detalhes
  if (selectedMatchId !== null) {
    return (
      <MatchDetails
        matchId={selectedMatchId}
        onBack={() => setSelectedMatchId(null)}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Filtros */}
      <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)]">
        <h2 className="text-lg font-semibold mb-4">Filtros</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs text-[var(--text-secondary)] mb-1">
              Time
            </label>
            <select
              value={selectedTeam || ""}
              onChange={(e) =>
                setSelectedTeam(e.target.value ? Number(e.target.value) : undefined)
              }
              className="w-full p-2 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded text-sm focus:outline-none focus:border-[var(--accent-blue)]"
            >
              <option value="">Todos</option>
              {teams.map((t) => (
                <option key={t.api_id} value={t.api_id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-[var(--text-secondary)] mb-1">
              Temporada
            </label>
            <select
              value={selectedSeason || ""}
              onChange={(e) =>
                setSelectedSeason(
                  e.target.value ? Number(e.target.value) : undefined
                )
              }
              className="w-full p-2 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded text-sm focus:outline-none focus:border-[var(--accent-blue)]"
            >
              <option value="">Todas</option>
              <option value="2026">2026</option>
              <option value="2025">2025</option>
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={handleSearch}
              className="w-full py-2 bg-[var(--accent-blue)] text-white rounded text-sm font-semibold hover:bg-blue-600 transition-colors"
            >
              Buscar
            </button>
          </div>
        </div>
      </div>

      {/* Lista */}
      <div className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-color)] overflow-hidden">
        {loading ? (
          <p className="p-6 text-center text-[var(--text-secondary)]">
            Carregando...
          </p>
        ) : matches.length === 0 ? (
          <p className="p-6 text-center text-[var(--text-secondary)]">
            Nenhuma partida encontrada. Clique em &quot;Buscar&quot; para
            carregar.
          </p>
        ) : (
          <div className="divide-y divide-[var(--border-color)]">
            {matches.map((m) => (
              <div
                key={m.id}
                onClick={() => setSelectedMatchId(m.id)}
                className="flex items-center justify-between px-4 py-3 hover:bg-[var(--bg-secondary)] transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2 flex-1 justify-end">
                  <span className="text-sm font-medium text-right">
                    {m.home_team.name}
                  </span>
                  {m.home_team.logo && (
                    <Image
                      src={m.home_team.logo}
                      alt={m.home_team.name}
                      width={24}
                      height={24}
                      className="rounded"
                    />
                  )}
                </div>

                <div className="px-4 text-center min-w-[80px]">
                  <span className="text-lg font-bold">
                    {m.home_goals} - {m.away_goals}
                  </span>
                  <p className="text-[10px] text-[var(--text-secondary)]">
                    {new Date(m.date).toLocaleDateString("pt-BR")}
                  </p>
                </div>

                <div className="flex items-center gap-2 flex-1">
                  {m.away_team.logo && (
                    <Image
                      src={m.away_team.logo}
                      alt={m.away_team.name}
                      width={24}
                      height={24}
                      className="rounded"
                    />
                  )}
                  <span className="text-sm font-medium">
                    {m.away_team.name}
                  </span>
                </div>

                <span className="text-[10px] text-[var(--text-secondary)] ml-2 hidden md:inline">
                  Detalhes →
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Paginação */}
        {totalPages > 1 && (
          <div className="flex justify-center gap-2 p-4 border-t border-[var(--border-color)]">
            <button
              onClick={() => fetchMatches(page - 1)}
              disabled={page <= 1}
              className="px-3 py-1 text-sm bg-[var(--bg-secondary)] rounded disabled:opacity-40"
            >
              Anterior
            </button>
            <span className="px-3 py-1 text-sm text-[var(--text-secondary)]">
              {page} / {totalPages}
            </span>
            <button
              onClick={() => fetchMatches(page + 1)}
              disabled={page >= totalPages}
              className="px-3 py-1 text-sm bg-[var(--bg-secondary)] rounded disabled:opacity-40"
            >
              Próximo
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
