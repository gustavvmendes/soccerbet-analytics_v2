"use client";

import { useState, useEffect } from "react";
import {
  getDataStatus,
  collectData,
  collectMultipleSeasons,
  trainModels,
  DataStatus,
} from "@/lib/api";

export default function DataManager() {
  const [status, setStatus] = useState<DataStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const res = await getDataStatus();
      setStatus(res.data);
    } catch {
      setError("Erro ao verificar status dos dados");
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleCollect = async (season: number) => {
    setLoading(true);
    setMessage(null);
    setError(null);
    try {
      const res = await collectData(season);
      setMessage(
        `Temporada ${season}: ${res.data.fixtures_processed} partidas processadas`
      );
      fetchStatus();
    } catch (err: any) {
      setError(err.response?.data?.error || "Erro na coleta");
    } finally {
      setLoading(false);
    }
  };

  const handleCollectBoth = async () => {
    setLoading(true);
    setMessage(null);
    setError(null);
    try {
      const res = await collectMultipleSeasons([2025, 2026]);
      const msgs = res.data.results.map(
        (r: any) =>
          `${r.season}: ${r.status === "success" ? r.fixtures_processed + " partidas" : r.error}`
      );
      setMessage(msgs.join(" | "));
      fetchStatus();
    } catch (err: any) {
      setError(err.response?.data?.error || "Erro na coleta");
    } finally {
      setLoading(false);
    }
  };

  const handleTrain = async () => {
    setLoading(true);
    setMessage(null);
    setError(null);
    try {
      const res = await trainModels([2025, 2026]);
      setMessage(
        `Modelos treinados! Dataset: ${res.data.dataset_size} amostras, ${res.data.xgboost?.models_count || 0} modelos XGBoost`
      );
      fetchStatus();
    } catch (err: any) {
      setError(err.response?.data?.error || "Erro no treino");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Status */}
      <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)]">
        <h2 className="text-lg font-semibold mb-4">Status dos Dados</h2>
        {status ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-[var(--accent-blue)]">
                {status.total_matches}
              </div>
              <p className="text-xs text-[var(--text-secondary)]">Partidas</p>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-[var(--accent-green)]">
                {status.total_teams}
              </div>
              <p className="text-xs text-[var(--text-secondary)]">Times</p>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-[var(--accent-yellow)]">
                {status.seasons.join(", ") || "—"}
              </div>
              <p className="text-xs text-[var(--text-secondary)]">
                Temporadas
              </p>
            </div>
            <div className="text-center">
              <div
                className={`text-2xl font-bold ${status.models_trained ? "text-[var(--accent-green)]" : "text-[var(--accent-red)]"}`}
              >
                {status.models_trained ? "Sim" : "Não"}
              </div>
              <p className="text-xs text-[var(--text-secondary)]">
                Modelos Treinados
              </p>
            </div>
          </div>
        ) : (
          <p className="text-[var(--text-secondary)]">Carregando...</p>
        )}
      </div>

      {/* Ações */}
      <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)]">
        <h2 className="text-lg font-semibold mb-4">Ações</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <button
            onClick={() => handleCollect(2025)}
            disabled={loading}
            className="py-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg text-sm hover:border-[var(--accent-blue)] disabled:opacity-40 transition-colors"
          >
            Coletar Temporada 2025
          </button>
          <button
            onClick={() => handleCollect(2026)}
            disabled={loading}
            className="py-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg text-sm hover:border-[var(--accent-blue)] disabled:opacity-40 transition-colors"
          >
            Coletar Temporada 2026
          </button>
          <button
            onClick={handleCollectBoth}
            disabled={loading}
            className="py-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg text-sm hover:border-[var(--accent-green)] disabled:opacity-40 transition-colors"
          >
            Coletar Ambas (2025 + 2026)
          </button>
          <button
            onClick={handleTrain}
            disabled={loading}
            className="py-3 bg-[var(--accent-blue)] text-white rounded-lg text-sm font-semibold hover:bg-blue-600 disabled:opacity-40 transition-colors"
          >
            Treinar Modelos
          </button>
        </div>

        {loading && (
          <p className="mt-4 text-sm text-[var(--accent-yellow)] text-center">
            Processando... isso pode levar alguns minutos.
          </p>
        )}
        {message && (
          <p className="mt-4 text-sm text-[var(--accent-green)] text-center">
            {message}
          </p>
        )}
        {error && (
          <p className="mt-4 text-sm text-[var(--accent-red)] text-center">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}
