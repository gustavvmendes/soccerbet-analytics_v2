"use client";

import { useState, useEffect } from "react";
import TeamSelector from "@/components/TeamSelector";
import PredictionDisplay from "@/components/PredictionDisplay";
import ScoreHeatmap from "@/components/ScoreHeatmap";
import DataManager from "@/components/DataManager";
import MatchHistory from "@/components/MatchHistory";
import UpcomingMatches from "@/components/UpcomingMatches";
import { Team, PredictionResult, getTeams, predict } from "@/lib/api";

type Tab = "predict" | "upcoming" | "history" | "data";

export default function Home() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [homeTeam, setHomeTeam] = useState<Team | null>(null);
  const [awayTeam, setAwayTeam] = useState<Team | null>(null);
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("predict");

  useEffect(() => {
    getTeams()
      .then((res) => setTeams(res.data))
      .catch(() => {});
  }, []);

  const handlePredict = async () => {
    if (!homeTeam || !awayTeam) return;
    setLoading(true);
    setError(null);
    setPrediction(null);

    try {
      const res = await predict(homeTeam.api_id, awayTeam.api_id);
      setPrediction(res.data);
    } catch (err: any) {
      setError(err.response?.data?.error || "Erro ao gerar predição");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="max-w-7xl mx-auto px-4 py-8">
      <header className="text-center mb-10">
        <h1 className="text-4xl font-bold mb-2">
          Predição Brasileirão Série A
        </h1>
        <p className="text-[var(--text-secondary)]">
          Análise preditiva utilizando Dixon-Coles + XGBoost
        </p>
      </header>

      {/* Tabs */}
      <nav className="flex gap-1 mb-8 bg-[var(--bg-secondary)] rounded-lg p-1 max-w-md mx-auto">
        {([
          ["predict", "Predição"],
          ["upcoming", "Próximos Jogos"],
          ["history", "Histórico"],
          ["data", "Dados"],
        ] as [Tab, string][]).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              activeTab === key
                ? "bg-[var(--accent-blue)] text-white"
                : "text-[var(--text-secondary)] hover:text-white"
            }`}
          >
            {label}
          </button>
        ))}
      </nav>

      {/* Tab: Predição */}
      {activeTab === "predict" && (
        <div>
          <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)] mb-8">
            <h2 className="text-lg font-semibold mb-4">Selecionar Confronto</h2>
            <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-4 items-end">
              <TeamSelector
                label="Time da Casa"
                teams={teams}
                selected={homeTeam}
                onSelect={setHomeTeam}
                excludeId={awayTeam?.api_id}
              />
              <span className="text-2xl font-bold text-center text-[var(--text-secondary)] pb-2">
                VS
              </span>
              <TeamSelector
                label="Time Visitante"
                teams={teams}
                selected={awayTeam}
                onSelect={setAwayTeam}
                excludeId={homeTeam?.api_id}
              />
            </div>
            <button
              onClick={handlePredict}
              disabled={!homeTeam || !awayTeam || loading}
              className="mt-6 w-full py-3 bg-[var(--accent-blue)] text-white font-semibold rounded-lg disabled:opacity-40 hover:bg-blue-600 transition-colors"
            >
              {loading ? "Calculando..." : "Gerar Predição"}
            </button>
            {error && (
              <p className="mt-4 text-[var(--accent-red)] text-sm text-center">
                {error}
              </p>
            )}
          </div>

          {prediction && (
            <div className="space-y-6">
              <PredictionDisplay prediction={prediction} />
              <ScoreHeatmap
                matrix={prediction.score_matrix}
                homeTeam={prediction.home_team.name}
                awayTeam={prediction.away_team.name}
              />
            </div>
          )}
        </div>
      )}

      {/* Tab: Próximos Jogos */}
      {activeTab === "upcoming" && (
        <UpcomingMatches
          onPredict={(p) => {
            setPrediction(p);
            setActiveTab("predict");
          }}
        />
      )}

      {/* Tab: Histórico */}
      {activeTab === "history" && <MatchHistory teams={teams} />}

      {/* Tab: Dados */}
      {activeTab === "data" && <DataManager />}
    </main>
  );
}
