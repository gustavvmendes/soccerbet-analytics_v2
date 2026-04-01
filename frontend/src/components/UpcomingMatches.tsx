"use client";

import { useState, useEffect } from "react";
import { MatchData, getUpcomingMatches, predict, PredictionResult } from "@/lib/api";
import Image from "next/image";

interface Props {
  onPredict: (prediction: PredictionResult) => void;
}

export default function UpcomingMatches({ onPredict }: Props) {
  const [matches, setMatches] = useState<MatchData[]>([]);
  const [loading, setLoading] = useState(false);
  const [predictingId, setPredictingId] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);

  const fetchMatches = async (p: number = 1) => {
    setLoading(true);
    try {
      const res = await getUpcomingMatches(p);
      setMatches(res.data.matches);
      setPage(res.data.page);
      setTotalPages(res.data.pages);
    } catch {
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMatches();
  }, []);

  const handlePredict = async (match: MatchData) => {
    setPredictingId(match.id);
    try {
      const res = await predict(match.home_team.api_id, match.away_team.api_id);
      onPredict(res.data);
    } catch {
    } finally {
      setPredictingId(null);
    }
  };

  return (
    <div className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-color)] overflow-hidden">
      <div className="p-4 border-b border-[var(--border-color)]">
        <h2 className="text-lg font-semibold">Próximos Jogos — Brasileirão 2026</h2>
        <p className="text-xs text-[var(--text-secondary)] mt-1">
          Clique em &quot;Prever&quot; para gerar a predição de uma partida
        </p>
      </div>

      {loading ? (
        <p className="p-6 text-center text-[var(--text-secondary)]">
          Carregando...
        </p>
      ) : matches.length === 0 ? (
        <p className="p-6 text-center text-[var(--text-secondary)]">
          Nenhum jogo futuro encontrado. Colete os dados de 2026 na aba Dados.
        </p>
      ) : (
        <div className="divide-y divide-[var(--border-color)]">
          {matches.map((m) => (
            <div
              key={m.id}
              className="flex items-center px-4 py-3 hover:bg-[var(--bg-secondary)] transition-colors"
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

              <div className="px-4 text-center min-w-[140px]">
                <p className="text-xs text-[var(--text-secondary)]">
                  {new Date(m.date).toLocaleDateString("pt-BR", {
                    day: "2-digit",
                    month: "2-digit",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
                <p className="text-[10px] text-[var(--text-secondary)] mt-0.5">
                  {m.round}
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

              <button
                onClick={() => handlePredict(m)}
                disabled={predictingId === m.id}
                className="ml-4 px-3 py-1.5 text-xs font-semibold bg-[var(--accent-blue)] text-white rounded-md hover:bg-blue-600 disabled:opacity-40 transition-colors"
              >
                {predictingId === m.id ? "..." : "Prever"}
              </button>
            </div>
          ))}
        </div>
      )}

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
  );
}
