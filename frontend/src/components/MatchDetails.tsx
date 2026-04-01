"use client";

import { useState, useEffect } from "react";
import { MatchData, PredictionResult, getMatchDetails } from "@/lib/api";
import Image from "next/image";

interface Props {
  matchId: number;
  onBack: () => void;
}

function CompareRow({
  label,
  real,
  predicted,
  format,
}: {
  label: string;
  real: number | null | undefined;
  predicted: number | null | undefined;
  format?: (v: number) => string;
}) {
  const fmt = format || ((v: number) => v.toFixed(1));
  return (
    <tr className="border-b border-[var(--border-color)]">
      <td className="py-2 px-3 text-sm">{label}</td>
      <td className="py-2 px-3 text-sm text-center font-medium">
        {real != null ? fmt(real) : "—"}
      </td>
      <td className="py-2 px-3 text-sm text-center font-medium text-[var(--accent-blue)]">
        {predicted != null ? fmt(predicted) : "—"}
      </td>
    </tr>
  );
}

function ProbBar({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  const pct = (value * 100).toFixed(1);
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span>{label}</span>
        <span className="font-semibold">{pct}%</span>
      </div>
      <div className="h-2 bg-[var(--bg-primary)] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

export default function MatchDetails({ matchId, onBack }: Props) {
  const [match, setMatch] = useState<MatchData | null>(null);
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getMatchDetails(matchId)
      .then((res) => {
        setMatch(res.data.match);
        setPrediction(res.data.prediction);
      })
      .catch(() => setError("Erro ao carregar detalhes"))
      .finally(() => setLoading(false));
  }, [matchId]);

  if (loading) {
    return (
      <p className="p-6 text-center text-[var(--text-secondary)]">
        Carregando detalhes...
      </p>
    );
  }

  if (error || !match) {
    return (
      <div className="text-center p-6">
        <p className="text-[var(--accent-red)] mb-4">{error || "Partida não encontrada"}</p>
        <button onClick={onBack} className="text-[var(--accent-blue)] text-sm underline">
          Voltar
        </button>
      </div>
    );
  }

  const stats = match.statistics;
  const xgb = prediction?.xgb_predictions;

  // Determinar resultado real
  const realResult =
    match.home_goals > match.away_goals
      ? "home"
      : match.home_goals < match.away_goals
        ? "away"
        : "draw";

  const realTotalGoals = (match.home_goals ?? 0) + (match.away_goals ?? 0);
  const realBtts = (match.home_goals ?? 0) > 0 && (match.away_goals ?? 0) > 0;

  // Determinar o que o modelo previu
  let predictedResult: string | null = null;
  if (prediction) {
    if (prediction.home_win_prob >= prediction.draw_prob && prediction.home_win_prob >= prediction.away_win_prob)
      predictedResult = "home";
    else if (prediction.away_win_prob >= prediction.draw_prob)
      predictedResult = "away";
    else
      predictedResult = "draw";
  }

  const resultCorrect = prediction && predictedResult === realResult;

  const confidenceColor =
    prediction?.confidence === "alta"
      ? "var(--accent-green)"
      : prediction?.confidence === "media"
        ? "var(--accent-yellow)"
        : "var(--accent-red)";

  return (
    <div className="space-y-6">
      {/* Voltar */}
      <button
        onClick={onBack}
        className="text-sm text-[var(--accent-blue)] hover:underline flex items-center gap-1"
      >
        ← Voltar ao histórico
      </button>

      {/* Cabeçalho: placar real */}
      <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)]">
        <p className="text-xs text-[var(--text-secondary)] text-center mb-1">
          {match.round} —{" "}
          {new Date(match.date).toLocaleDateString("pt-BR", {
            weekday: "long",
            day: "2-digit",
            month: "long",
            year: "numeric",
          })}
        </p>

        <div className="grid grid-cols-3 items-center text-center gap-4 mt-4">
          <div className="flex flex-col items-center gap-2">
            {match.home_team.logo && (
              <Image src={match.home_team.logo} alt={match.home_team.name} width={64} height={64} />
            )}
            <span className="font-semibold text-sm">{match.home_team.name}</span>
          </div>
          <div>
            <div className="text-5xl font-bold">
              {match.home_goals} - {match.away_goals}
            </div>
            <p className="text-xs text-[var(--text-secondary)] mt-1">Resultado Final</p>
          </div>
          <div className="flex flex-col items-center gap-2">
            {match.away_team.logo && (
              <Image src={match.away_team.logo} alt={match.away_team.name} width={64} height={64} />
            )}
            <span className="font-semibold text-sm">{match.away_team.name}</span>
          </div>
        </div>
      </div>

      {/* Predição vs Real - resumo */}
      {prediction && (
        <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)]">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
              Predição do Modelo
            </h3>
            <div className="flex items-center gap-3">
              <span
                className="text-xs font-semibold px-2 py-1 rounded"
                style={{ backgroundColor: confidenceColor, color: "#fff" }}
              >
                Confiança {prediction.confidence}
              </span>
              <span
                className={`text-xs font-semibold px-2 py-1 rounded ${
                  resultCorrect
                    ? "bg-green-600 text-white"
                    : "bg-red-600 text-white"
                }`}
              >
                {resultCorrect ? "✓ Acertou" : "✗ Errou"}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-3 items-center text-center gap-4 mb-6">
            <div>
              <div className="text-3xl font-bold text-[var(--accent-blue)]">
                {prediction.most_likely_score.home} - {prediction.most_likely_score.away}
              </div>
              <p className="text-xs text-[var(--text-secondary)] mt-1">Placar Previsto</p>
            </div>
            <div>
              <div className="text-3xl font-bold">
                {match.home_goals} - {match.away_goals}
              </div>
              <p className="text-xs text-[var(--text-secondary)] mt-1">Placar Real</p>
            </div>
            <div>
              <div className="text-2xl font-bold">
                λ {prediction.lambda_home.toFixed(2)} - {prediction.lambda_away.toFixed(2)}
              </div>
              <p className="text-xs text-[var(--text-secondary)] mt-1">xG (Gols Esperados)</p>
            </div>
          </div>

          {/* Probabilidades de resultado */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="text-xs font-semibold text-[var(--text-secondary)] uppercase mb-3">
                Probabilidades de Resultado
              </h4>
              <div className="space-y-3">
                <ProbBar
                  label={`Vitória ${match.home_team.name}`}
                  value={prediction.home_win_prob}
                  color={realResult === "home" ? "var(--accent-green)" : "var(--accent-blue)"}
                />
                <ProbBar
                  label="Empate"
                  value={prediction.draw_prob}
                  color={realResult === "draw" ? "var(--accent-green)" : "var(--accent-yellow)"}
                />
                <ProbBar
                  label={`Vitória ${match.away_team.name}`}
                  value={prediction.away_win_prob}
                  color={realResult === "away" ? "var(--accent-green)" : "var(--accent-red)"}
                />
              </div>
            </div>

            <div>
              <h4 className="text-xs font-semibold text-[var(--text-secondary)] uppercase mb-3">
                Over/Under & BTTS
              </h4>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span>Over 0.5</span>
                  <span className="font-medium">
                    Previsto: {(prediction.over_05 * 100).toFixed(0)}% | Real:{" "}
                    <span className={realTotalGoals > 0.5 ? "text-green-400" : "text-red-400"}>
                      {realTotalGoals > 0.5 ? "Sim" : "Não"}
                    </span>
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Over 1.5</span>
                  <span className="font-medium">
                    Previsto: {(prediction.over_15 * 100).toFixed(0)}% | Real:{" "}
                    <span className={realTotalGoals > 1.5 ? "text-green-400" : "text-red-400"}>
                      {realTotalGoals > 1.5 ? "Sim" : "Não"}
                    </span>
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Over 2.5</span>
                  <span className="font-medium">
                    Previsto: {(prediction.over_25 * 100).toFixed(0)}% | Real:{" "}
                    <span className={realTotalGoals > 2.5 ? "text-green-400" : "text-red-400"}>
                      {realTotalGoals > 2.5 ? "Sim" : "Não"}
                    </span>
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Over 3.5</span>
                  <span className="font-medium">
                    Previsto: {(prediction.over_35 * 100).toFixed(0)}% | Real:{" "}
                    <span className={realTotalGoals > 3.5 ? "text-green-400" : "text-red-400"}>
                      {realTotalGoals > 3.5 ? "Sim" : "Não"}
                    </span>
                  </span>
                </div>
                <div className="border-t border-[var(--border-color)] pt-2 flex justify-between text-sm">
                  <span>BTTS (Ambas Marcam)</span>
                  <span className="font-medium">
                    Previsto: {(prediction.btts_prob * 100).toFixed(0)}% | Real:{" "}
                    <span className={realBtts ? "text-green-400" : "text-red-400"}>
                      {realBtts ? "Sim" : "Não"}
                    </span>
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tabela comparativa: estatísticas reais vs previstas */}
      {(stats || xgb) && (
        <div className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-color)] overflow-hidden">
          <div className="p-4 border-b border-[var(--border-color)]">
            <h3 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
              Estatísticas — Real vs Modelo
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-0 md:divide-x divide-[var(--border-color)]">
            {/* Casa */}
            <div>
              <div className="px-4 py-2 bg-[var(--bg-secondary)] text-center text-xs font-semibold uppercase tracking-wider">
                {match.home_team.name} (Casa)
              </div>
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[var(--border-color)] text-[var(--text-secondary)]">
                    <th className="py-2 px-3 text-xs text-left font-medium">Estatística</th>
                    <th className="py-2 px-3 text-xs text-center font-medium">Real</th>
                    <th className="py-2 px-3 text-xs text-center font-medium">Previsto</th>
                  </tr>
                </thead>
                <tbody>
                  <CompareRow label="Gols" real={match.home_goals} predicted={prediction?.lambda_home} />
                  <CompareRow label="Posse de Bola (%)" real={stats?.home_possession} predicted={xgb?.home_possession} />
                  <CompareRow label="Chutes Totais" real={stats?.home_shots_total} predicted={xgb?.home_shots} />
                  <CompareRow label="Escanteios" real={stats?.home_corners} predicted={xgb?.home_corners} />
                  <CompareRow label="Cartões Amarelos" real={stats?.home_yellow_cards} predicted={xgb?.home_cards} />
                  <CompareRow label="Faltas" real={stats?.home_fouls} predicted={null} />
                  <CompareRow
                    label="Chutes no Gol"
                    real={stats?.home_shots_on_target}
                    predicted={null}
                  />
                </tbody>
              </table>
            </div>

            {/* Visitante */}
            <div>
              <div className="px-4 py-2 bg-[var(--bg-secondary)] text-center text-xs font-semibold uppercase tracking-wider">
                {match.away_team.name} (Visitante)
              </div>
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[var(--border-color)] text-[var(--text-secondary)]">
                    <th className="py-2 px-3 text-xs text-left font-medium">Estatística</th>
                    <th className="py-2 px-3 text-xs text-center font-medium">Real</th>
                    <th className="py-2 px-3 text-xs text-center font-medium">Previsto</th>
                  </tr>
                </thead>
                <tbody>
                  <CompareRow label="Gols" real={match.away_goals} predicted={prediction?.lambda_away} />
                  <CompareRow label="Posse de Bola (%)" real={stats?.away_possession} predicted={xgb?.away_possession} />
                  <CompareRow label="Chutes Totais" real={stats?.away_shots_total} predicted={xgb?.away_shots} />
                  <CompareRow label="Escanteios" real={stats?.away_corners} predicted={xgb?.away_corners} />
                  <CompareRow label="Cartões Amarelos" real={stats?.away_yellow_cards} predicted={xgb?.away_cards} />
                  <CompareRow label="Faltas" real={stats?.away_fouls} predicted={null} />
                  <CompareRow
                    label="Chutes no Gol"
                    real={stats?.away_shots_on_target}
                    predicted={null}
                  />
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Sem predição */}
      {!prediction && (
        <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)] text-center">
          <p className="text-[var(--text-secondary)] text-sm">
            Modelos não treinados — treine na aba Dados para ver a comparação com a predição.
          </p>
        </div>
      )}
    </div>
  );
}
