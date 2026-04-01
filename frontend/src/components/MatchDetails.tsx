"use client";

import { useState, useEffect } from "react";
import { MatchData, PredictionResult, getMatchDetails } from "@/lib/api";
import ScoreHeatmap from "./ScoreHeatmap";
import Image from "next/image";

// Calcula P(X > threshold) usando Poisson CDF
function poissonOver(lambda: number, threshold: number): number {
  // P(X > k) = 1 - P(X <= k)
  const k = Math.floor(threshold);
  let cdf = 0;
  let term = Math.exp(-lambda);
  cdf += term;
  for (let i = 1; i <= k; i++) {
    term *= lambda / i;
    cdf += term;
  }
  return 1 - cdf;
}

interface Props {
  matchId: number;
  onBack: () => void;
  backLabel?: string;
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

function StatRow({
  label,
  home,
  away,
}: {
  label: string;
  home: number;
  away: number;
}) {
  const total = home + away || 1;
  const hPct = (home / total) * 100;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="font-medium">{home.toFixed(1)}</span>
        <span className="text-[var(--text-secondary)]">{label}</span>
        <span className="font-medium">{away.toFixed(1)}</span>
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

export default function MatchDetails({ matchId, onBack, backLabel }: Props) {
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

  const isFinished = match.status === "FT";
  const stats = match.statistics;
  const xgb = prediction?.xgb_predictions;

  // Dados de jogo finalizado
  const realResult = isFinished
    ? match.home_goals > match.away_goals
      ? "home"
      : match.home_goals < match.away_goals
        ? "away"
        : "draw"
    : null;

  const realTotalGoals = isFinished ? (match.home_goals ?? 0) + (match.away_goals ?? 0) : null;
  const realBtts = isFinished ? (match.home_goals ?? 0) > 0 && (match.away_goals ?? 0) > 0 : null;

  let predictedResult: string | null = null;
  if (prediction) {
    if (prediction.home_win_prob >= prediction.draw_prob && prediction.home_win_prob >= prediction.away_win_prob)
      predictedResult = "home";
    else if (prediction.away_win_prob >= prediction.draw_prob)
      predictedResult = "away";
    else
      predictedResult = "draw";
  }

  const resultCorrect = isFinished && prediction && predictedResult === realResult;

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
        ← {backLabel || "Voltar"}
      </button>

      {/* Cabeçalho */}
      <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)]">
        <p className="text-xs text-[var(--text-secondary)] text-center mb-1">
          {match.round} —{" "}
          {new Date(match.date).toLocaleDateString("pt-BR", {
            weekday: "long",
            day: "2-digit",
            month: "long",
            year: "numeric",
            ...(isFinished ? {} : { hour: "2-digit", minute: "2-digit" }),
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
            {isFinished ? (
              <>
                <div className="text-5xl font-bold">
                  {match.home_goals} - {match.away_goals}
                </div>
                <p className="text-xs text-[var(--text-secondary)] mt-1">Resultado Final</p>
              </>
            ) : (
              <>
                <div className="text-3xl font-bold text-[var(--text-secondary)]">VS</div>
                <p className="text-xs text-[var(--accent-yellow)] mt-1 font-semibold">A realizar</p>
              </>
            )}
          </div>
          <div className="flex flex-col items-center gap-2">
            {match.away_team.logo && (
              <Image src={match.away_team.logo} alt={match.away_team.name} width={64} height={64} />
            )}
            <span className="font-semibold text-sm">{match.away_team.name}</span>
          </div>
        </div>
      </div>

      {/* Predição */}
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
              {isFinished && (
                <span
                  className={`text-xs font-semibold px-2 py-1 rounded ${
                    resultCorrect ? "bg-green-600 text-white" : "bg-red-600 text-white"
                  }`}
                >
                  {resultCorrect ? "✓ Acertou" : "✗ Errou"}
                </span>
              )}
            </div>
          </div>

          {/* Placar previsto + xG */}
          <div className={`grid items-center text-center gap-4 mb-6 ${isFinished ? "grid-cols-3" : "grid-cols-1"}`}>
            <div>
              <div className="text-3xl font-bold text-[var(--accent-blue)]">
                {prediction.most_likely_score.home} - {prediction.most_likely_score.away}
              </div>
              <p className="text-xs text-[var(--text-secondary)] mt-1">Placar Previsto</p>
            </div>
            {isFinished && (
              <div>
                <div className="text-3xl font-bold">
                  {match.home_goals} - {match.away_goals}
                </div>
                <p className="text-xs text-[var(--text-secondary)] mt-1">Placar Real</p>
              </div>
            )}
          </div>

          {/* xG (Gols Esperados) */}
          <div className="flex justify-center gap-8 mb-6">
            <div className="text-center">
              <p className="text-xs text-[var(--text-secondary)] mb-1">{match.home_team.name}</p>
              <span className="text-2xl font-bold text-[var(--accent-blue)]">
                {prediction.lambda_home.toFixed(2)}
              </span>
            </div>
            <div className="text-center flex flex-col justify-end">
              <p className="text-xs text-[var(--text-secondary)] mb-1">xG</p>
              <span className="text-sm text-[var(--text-secondary)]">Gols Esperados</span>
            </div>
            <div className="text-center">
              <p className="text-xs text-[var(--text-secondary)] mb-1">{match.away_team.name}</p>
              <span className="text-2xl font-bold text-[var(--accent-red)]">
                {prediction.lambda_away.toFixed(2)}
              </span>
            </div>
          </div>

          {/* Probabilidades */}
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
                {[
                  { label: "Over 0.5", prob: prediction.over_05, threshold: 0.5 },
                  { label: "Over 1.5", prob: prediction.over_15, threshold: 1.5 },
                  { label: "Over 2.5", prob: prediction.over_25, threshold: 2.5 },
                  { label: "Over 3.5", prob: prediction.over_35, threshold: 3.5 },
                ].map(({ label, prob, threshold }) => (
                  <div key={label}>
                    <ProbBar
                      label={
                        realTotalGoals != null
                          ? `${label} ${realTotalGoals > threshold ? "✓" : "✗"}`
                          : label
                      }
                      value={prob}
                      color={
                        realTotalGoals != null
                          ? realTotalGoals > threshold
                            ? "var(--accent-green)"
                            : "var(--accent-red)"
                          : "var(--accent-blue)"
                      }
                    />
                  </div>
                ))}
                <div className="border-t border-[var(--border-color)] pt-3">
                  <ProbBar
                    label={
                      realBtts != null
                        ? `BTTS (Ambas Marcam) ${realBtts ? "✓" : "✗"}`
                        : "BTTS (Ambas Marcam)"
                    }
                    value={prediction.btts_prob}
                    color={
                      realBtts != null
                        ? realBtts
                          ? "var(--accent-green)"
                          : "var(--accent-red)"
                        : "var(--accent-yellow)"
                    }
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Estatísticas previstas (jogos futuros — sem dados reais) */}
      {!isFinished && xgb && (() => {
        const totalShots = xgb.home_shots + xgb.away_shots;
        const totalCorners = xgb.home_corners + xgb.away_corners;
        const totalCards = xgb.home_cards + xgb.away_cards;

        const statGroups = [
          {
            title: "Posse de Bola",
            type: "possession" as const,
            home: xgb.home_possession,
            away: xgb.away_possession,
          },
          {
            title: "Chutes Totais",
            subtitle: `Previsão: ${totalShots.toFixed(1)} chutes`,
            lambda: totalShots,
            thresholds: [16.5, 18.5, 20.5, 22.5, 24.5],
          },
          {
            title: "Escanteios",
            subtitle: `Previsão: ${totalCorners.toFixed(1)} escanteios`,
            lambda: totalCorners,
            thresholds: [6.5, 7.5, 8.5, 9.5, 10.5],
          },
          {
            title: "Cartões",
            subtitle: `Previsão: ${totalCards.toFixed(1)} cartões`,
            lambda: totalCards,
            thresholds: [2.5, 3.5, 4.5, 5.5, 6.5],
          },
        ];

        return (
          <div className="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)]">
            <h3 className="text-sm font-semibold mb-4 text-[var(--text-secondary)] uppercase tracking-wider">
              Estatísticas Previstas
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {statGroups.map((group) => (
                <div key={group.title}>
                  <h4 className="text-xs font-semibold text-[var(--text-secondary)] uppercase mb-1">
                    {group.title}
                  </h4>
                  {group.type === "possession" ? (
                    <>
                      <p className="text-[10px] text-[var(--text-secondary)] mb-3">
                        {match.home_team.name} {group.home!.toFixed(1)}% — {match.away_team.name} {group.away!.toFixed(1)}%
                      </p>
                      <StatRow label="Posse de Bola (%)" home={group.home!} away={group.away!} />
                    </>
                  ) : (
                    <>
                      <p className="text-[10px] text-[var(--text-secondary)] mb-3">{group.subtitle}</p>
                      <div className="space-y-3">
                        {group.thresholds!.map((t) => (
                          <ProbBar
                            key={t}
                            label={`Over ${t}`}
                            value={poissonOver(group.lambda!, t)}
                            color="var(--accent-blue)"
                          />
                        ))}
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        );
      })()}

      {/* Heatmap de placares (jogos futuros) */}
      {!isFinished && prediction?.score_matrix && (
        <ScoreHeatmap
          matrix={prediction.score_matrix}
          homeTeam={match.home_team.name}
          awayTeam={match.away_team.name}
        />
      )}

      {/* Tabela comparativa (jogos finalizados) */}
      {isFinished && (stats || xgb) && (
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
                  <CompareRow label="Chutes no Gol" real={stats?.home_shots_on_target} predicted={null} />
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
                  <CompareRow label="Chutes no Gol" real={stats?.away_shots_on_target} predicted={null} />
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
            Modelos não treinados — treine na aba Dados para ver a predição.
          </p>
        </div>
      )}
    </div>
  );
}
