"use client";

import { useState, useEffect } from "react";
import {
  MatchData, PredictionResult, getMatchDetails,
  OddsData, InjuryTeam, LineupTeam, ExplanationData,
  getMatchOdds, getMatchInjuries, getMatchLineups, getMatchExplanation,
} from "@/lib/api";
import PlayerMatchPrediction from "./PlayerMatchPrediction";
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

function OddsRow({
  label,
  modelProb,
  oddsProb,
  odd,
}: {
  label: string;
  modelProb: number;
  oddsProb: number | null | undefined;
  odd: number | null | undefined;
}) {
  const hasValue = oddsProb != null && modelProb > oddsProb;
  return (
    <tr className="border-b border-[var(--border-color)]">
      <td className="py-2 px-3 text-sm">{label}</td>
      <td className="py-2 px-3 text-sm text-center font-medium text-[var(--accent-blue)]">
        {(modelProb * 100).toFixed(1)}%
      </td>
      <td className="py-2 px-3 text-sm text-center font-medium">
        {oddsProb != null ? (
          <span className={hasValue ? "text-[var(--accent-green)]" : ""}>
            {(oddsProb * 100).toFixed(1)}%
          </span>
        ) : "—"}
      </td>
      <td className="py-2 px-3 text-sm text-center text-[var(--text-secondary)]">
        {odd != null ? odd.toFixed(2) : "—"}
      </td>
    </tr>
  );
}

function FeatureRow({
  label,
  value,
  pct,
  suffix,
}: {
  label: string;
  value: number | undefined;
  pct?: boolean;
  suffix?: string;
}) {
  if (value == null) return null;
  const display = pct ? `${(value * 100).toFixed(0)}%` : `${value.toFixed(1)}${suffix || ""}`;
  return (
    <div className="flex justify-between py-0.5 px-2 rounded odd:bg-[var(--bg-secondary)]">
      <span className="text-[var(--text-secondary)]">{label}</span>
      <span className="font-medium">{display}</span>
    </div>
  );
}

export default function MatchDetails({ matchId, onBack, backLabel }: Props) {
  const [match, setMatch] = useState<MatchData | null>(null);
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [odds, setOdds] = useState<OddsData | null>(null);
  const [injuries, setInjuries] = useState<InjuryTeam[]>([]);
  const [lineups, setLineups] = useState<LineupTeam[]>([]);
  const [explanation, setExplanation] = useState<ExplanationData | null>(null);
  const [selectedPlayerApiId, setSelectedPlayerApiId] = useState<number | null>(null);
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

    // Fetch supplementary data in parallel
    getMatchOdds(matchId).then((r) => setOdds(r.data)).catch(() => {});
    getMatchInjuries(matchId).then((r) => setInjuries(r.data || [])).catch(() => {});
    getMatchLineups(matchId).then((r) => setLineups(r.data || [])).catch(() => {});
    getMatchExplanation(matchId).then((r) => setExplanation(r.data)).catch(() => {});
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

  // Se um jogador foi selecionado, renderizar a predição individual
  if (selectedPlayerApiId) {
    return (
      <PlayerMatchPrediction
        matchId={matchId}
        playerApiId={selectedPlayerApiId}
        onBack={() => setSelectedPlayerApiId(null)}
      />
    );
  }

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

        const overUnderGroups = [
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
          <>
            {/* Estatísticas por time */}
            <div className="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)]">
              <h3 className="text-sm font-semibold mb-4 text-[var(--text-secondary)] uppercase tracking-wider">
                Estatísticas Previstas por Time
              </h3>
              <div className="space-y-4">
                <StatRow label="Posse de Bola (%)" home={xgb.home_possession} away={xgb.away_possession} />
                <StatRow label="Chutes" home={xgb.home_shots} away={xgb.away_shots} />
                <StatRow label="Escanteios" home={xgb.home_corners} away={xgb.away_corners} />
                <StatRow label="Cartões" home={xgb.home_cards} away={xgb.away_cards} />
              </div>
              <div className="flex justify-between text-[10px] text-[var(--text-secondary)] mt-3 px-1">
                <span>{match.home_team.name}</span>
                <span>{match.away_team.name}</span>
              </div>
            </div>

            {/* Over/Under totais */}
            <div className="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)]">
              <h3 className="text-sm font-semibold mb-4 text-[var(--text-secondary)] uppercase tracking-wider">
                Over/Under — Estatísticas Totais
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {overUnderGroups.map((group) => (
                  <div key={group.title}>
                    <h4 className="text-xs font-semibold text-[var(--text-secondary)] uppercase mb-1">
                      {group.title}
                    </h4>
                    <p className="text-[10px] text-[var(--text-secondary)] mb-3">{group.subtitle}</p>
                    <div className="space-y-3">
                      {group.thresholds.map((t) => (
                        <ProbBar
                          key={t}
                          label={`Over ${t}`}
                          value={poissonOver(group.lambda, t)}
                          color="var(--accent-blue)"
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        );
      })()}

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

      {/* ─── Odds: Modelo vs Casas de Apostas (COMENTADO) ─── */}
      {/* {odds && prediction && (
        <div className="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)]">
          <h3 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-4">
            Modelo vs Casas de Apostas ({odds.bookmaker})
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-color)] text-[var(--text-secondary)]">
                  <th className="py-2 px-3 text-left font-medium">Mercado</th>
                  <th className="py-2 px-3 text-center font-medium">Modelo</th>
                  <th className="py-2 px-3 text-center font-medium">Odds Impl.</th>
                  <th className="py-2 px-3 text-center font-medium">Odd</th>
                </tr>
              </thead>
              <tbody>
                <OddsRow
                  label={`Vitória ${match!.home_team.name}`}
                  modelProb={prediction.home_win_prob}
                  oddsProb={odds.match_winner_probs?.home}
                  odd={odds.match_winner?.home}
                />
                <OddsRow label="Empate" modelProb={prediction.draw_prob} oddsProb={odds.match_winner_probs?.draw} odd={odds.match_winner?.draw} />
                <OddsRow
                  label={`Vitória ${match!.away_team.name}`}
                  modelProb={prediction.away_win_prob}
                  oddsProb={odds.match_winner_probs?.away}
                  odd={odds.match_winner?.away}
                />
                {odds.over_under_25?.over && (
                  <OddsRow label="Over 2.5" modelProb={prediction.over_25} oddsProb={odds.over_under_25.over ? 1 / odds.over_under_25.over : null} odd={odds.over_under_25.over} />
                )}
                {odds.over_under_25?.under && (
                  <OddsRow label="Under 2.5" modelProb={1 - prediction.over_25} oddsProb={odds.over_under_25.under ? 1 / odds.over_under_25.under : null} odd={odds.over_under_25.under} />
                )}
                {odds.btts?.yes && (
                  <OddsRow label="BTTS Sim" modelProb={prediction.btts_prob} oddsProb={odds.btts.yes ? 1 / odds.btts.yes : null} odd={odds.btts.yes} />
                )}
              </tbody>
            </table>
          </div>
          <p className="text-[10px] text-[var(--text-secondary)] mt-3">
            Verde = modelo vê valor (probabilidade do modelo {'>'} probabilidade da odd). Odds <b>não</b> influenciam o modelo.
          </p>
        </div>
      )} */}

      {/* ─── Lesões / Suspensões ─── */}
      {injuries.length > 0 && (
        <div className="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)]">
          <h3 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-4">
            Lesões e Suspensões
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {injuries.map((team) => (
              <div key={team.team.api_id}>
                <div className="flex items-center gap-2 mb-2">
                  {team.team.logo && (
                    <Image src={team.team.logo} alt={team.team.name} width={20} height={20} />
                  )}
                  <span className="text-sm font-semibold">{team.team.name}</span>
                  <span className="text-[10px] text-[var(--accent-red)]">({team.injuries.length})</span>
                </div>
                <div className="space-y-1">
                  {team.injuries.map((inj, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-sm py-1 px-2 rounded bg-[var(--bg-secondary)]">
                      {inj.player_photo && (
                        <Image src={inj.player_photo} alt={inj.player_name} width={24} height={24} className="rounded-full" />
                      )}
                      <span className="flex-1">{inj.player_name}</span>
                      <span className="text-[10px] text-[var(--accent-red)]">{inj.reason || inj.type}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ─── Escalações (jogos finalizados) ─── */}
      {lineups.length > 0 && (
        <div className="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)]">
          <h3 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-4">
            Escalações
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {lineups.map((team) => (
              <div key={team.team.api_id}>
                <div className="flex items-center gap-2 mb-2">
                  {team.team.logo && (
                    <Image src={team.team.logo} alt={team.team.name} width={20} height={20} />
                  )}
                  <span className="text-sm font-semibold">{team.team.name}</span>
                  {team.formation && (
                    <span className="text-[10px] bg-[var(--bg-secondary)] px-1.5 py-0.5 rounded">{team.formation}</span>
                  )}
                </div>
                <div className="text-xs space-y-0.5">
                  <p className="text-[var(--text-secondary)] font-medium mb-1">Titulares</p>
                  {team.starters.map((p) => (
                    <button
                      key={p.player_api_id}
                      onClick={() => setSelectedPlayerApiId(p.player_api_id)}
                      className="flex gap-2 py-0.5 w-full text-left hover:bg-[var(--bg-secondary)] rounded px-1 transition-colors group"
                    >
                      <span className="text-[var(--text-secondary)] w-5 text-right">{p.player_number || ""}</span>
                      <span className="text-[var(--accent-blue)] w-4">{p.player_pos || ""}</span>
                      <span className="group-hover:text-[var(--accent-blue)] transition-colors">{p.player_name}</span>
                      <span className="ml-auto text-[9px] text-[var(--text-secondary)] opacity-0 group-hover:opacity-100 transition-opacity">Ver predição →</span>
                    </button>
                  ))}
                  {team.substitutes.length > 0 && (
                    <>
                      <p className="text-[var(--text-secondary)] font-medium mt-2 mb-1">Reservas</p>
                      {team.substitutes.map((p) => (
                        <button
                          key={p.player_api_id}
                          onClick={() => setSelectedPlayerApiId(p.player_api_id)}
                          className="flex gap-2 py-0.5 w-full text-left text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] rounded px-1 transition-colors group"
                        >
                          <span className="w-5 text-right">{p.player_number || ""}</span>
                          <span className="w-4">{p.player_pos || ""}</span>
                          <span className="group-hover:text-[var(--accent-blue)] transition-colors">{p.player_name}</span>
                          <span className="ml-auto text-[9px] opacity-0 group-hover:opacity-100 transition-opacity">Ver predição →</span>
                        </button>
                      ))}
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ─── Explicação da Predição ─── */}
      {explanation && (explanation.key_factors.length > 0 || explanation.dixon_coles) && (
        <div className="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)]">
          <h3 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-4">
            Por que esta Predição?
          </h3>

          {/* Fatores-chave */}
          {explanation.key_factors.length > 0 && (
            <div className="space-y-2 mb-5">
              {explanation.key_factors.map((f, i) => (
                <div
                  key={i}
                  className="text-sm py-2 px-3 rounded"
                  style={{
                    backgroundColor:
                      f.type === "positive_home" ? "rgba(34,197,94,0.08)"
                      : f.type === "positive_away" ? "rgba(239,68,68,0.08)"
                      : f.type === "negative_home" ? "rgba(239,68,68,0.06)"
                      : f.type === "prediction" ? "rgba(59,130,246,0.08)"
                      : f.type === "h2h" ? "rgba(234,179,8,0.08)"
                      : "rgba(156,163,175,0.06)",
                  }}
                >
                  <div className="flex items-start gap-2">
                    <span className="flex-shrink-0 mt-0.5">
                      {f.type === "positive_home" || f.type === "positive_away" ? "✅"
                      : f.type === "negative_home" ? "⚠️"
                      : f.type === "prediction" ? "📐"
                      : f.type === "h2h" ? "🔄"
                      : f.type === "xgboost_context" ? "📊"
                      : "ℹ️"}
                    </span>
                    <span>{f.text}</span>
                  </div>
                  {(f.subtext || f.technical) && (
                    <div className="ml-7 mt-1">
                      {f.subtext && (
                        <p className="text-xs text-[var(--text-secondary)]">{f.subtext}</p>
                      )}
                      {f.technical && (
                        <details className="mt-1 text-xs">
                          <summary className="cursor-pointer text-[var(--text-secondary)] hover:text-[var(--text-primary)] select-none">
                            Ver cálculo técnico
                          </summary>
                          <code className="block mt-1 px-2 py-1 bg-[var(--bg-secondary)] rounded text-[var(--text-secondary)] font-mono">
                            {f.technical}
                          </code>
                        </details>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Dixon-Coles details */}
          {explanation.dixon_coles && (
            <div>
              <h4 className="text-xs font-semibold text-[var(--text-secondary)] uppercase mb-1">
                Força das equipes — Ataque e Defesa
              </h4>
              <p className="text-[11px] text-[var(--text-secondary)] mb-3">
                Posição de cada time no ranking do campeonato, calculada a partir do histórico de gols marcados e sofridos na temporada.
              </p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center text-sm">
                <div className="bg-[var(--bg-secondary)] rounded-lg p-3">
                  <div className="text-lg font-bold text-[var(--accent-blue)]">
                    {explanation.dixon_coles.home_attack_rank}º
                  </div>
                  <div className="text-[10px] text-[var(--text-secondary)]">
                    Ataque {match!.home_team.name.split(" ")[0]}
                  </div>
                  <div className="text-[10px] text-[var(--text-secondary)] opacity-60 mt-0.5">
                    índice: {explanation.dixon_coles.home_attack.toFixed(3)}
                  </div>
                </div>
                <div className="bg-[var(--bg-secondary)] rounded-lg p-3">
                  <div className="text-lg font-bold text-[var(--accent-blue)]">
                    {explanation.dixon_coles.home_defense_rank}º
                  </div>
                  <div className="text-[10px] text-[var(--text-secondary)]">
                    Defesa {match!.home_team.name.split(" ")[0]}
                  </div>
                  <div className="text-[10px] text-[var(--text-secondary)] opacity-60 mt-0.5">
                    índice: {explanation.dixon_coles.home_defense.toFixed(3)}
                  </div>
                </div>
                <div className="bg-[var(--bg-secondary)] rounded-lg p-3">
                  <div className="text-lg font-bold text-[var(--accent-red)]">
                    {explanation.dixon_coles.away_attack_rank}º
                  </div>
                  <div className="text-[10px] text-[var(--text-secondary)]">
                    Ataque {match!.away_team.name.split(" ")[0]}
                  </div>
                  <div className="text-[10px] text-[var(--text-secondary)] opacity-60 mt-0.5">
                    índice: {explanation.dixon_coles.away_attack.toFixed(3)}
                  </div>
                </div>
                <div className="bg-[var(--bg-secondary)] rounded-lg p-3">
                  <div className="text-lg font-bold text-[var(--accent-red)]">
                    {explanation.dixon_coles.away_defense_rank}º
                  </div>
                  <div className="text-[10px] text-[var(--text-secondary)]">
                    Defesa {match!.away_team.name.split(" ")[0]}
                  </div>
                  <div className="text-[10px] text-[var(--text-secondary)] opacity-60 mt-0.5">
                    índice: {explanation.dixon_coles.away_defense.toFixed(3)}
                  </div>
                </div>
              </div>
              <p className="text-[10px] text-[var(--text-secondary)] mt-2 text-center">
                Posições de 1º (melhor) a {explanation.dixon_coles.total_teams}º (pior) entre os times do campeonato. O índice abaixo é o valor numérico usado pelo modelo Dixon-Coles.
              </p>
            </div>
          )}

          {/* Forma recente das equipes */}
          {explanation.features && (
            <div className="mt-5">
              <h4 className="text-xs font-semibold text-[var(--text-secondary)] uppercase mb-1">
                Forma Recente das Equipes
              </h4>
              <p className="text-[11px] text-[var(--text-secondary)] mb-3">
                Médias dos últimos jogos de cada time, considerando apenas atuações em casa (mandante) e fora (visitante).
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="font-semibold text-xs mb-2">{match!.home_team.name} (Casa)</p>
                  <div className="space-y-1 text-xs">
                    <FeatureRow label="Gols marcados/jogo" value={explanation.features.home_as_home?.avg_goals_scored} />
                    <FeatureRow label="Gols sofridos/jogo" value={explanation.features.home_as_home?.avg_goals_conceded} />
                    <FeatureRow label="Chutes/jogo" value={explanation.features.home_as_home?.avg_shots} />
                    <FeatureRow label="Escanteios/jogo" value={explanation.features.home_as_home?.avg_corners} />
                    <FeatureRow label="Taxa de vitória (casa)" value={explanation.features.home_as_home?.win_rate} pct />
                    <FeatureRow label="Posse média" value={explanation.features.home_as_home?.avg_possession} suffix="%" />
                  </div>
                </div>
                <div>
                  <p className="font-semibold text-xs mb-2">{match!.away_team.name} (Fora)</p>
                  <div className="space-y-1 text-xs">
                    <FeatureRow label="Gols marcados/jogo" value={explanation.features.away_as_away?.avg_goals_scored} />
                    <FeatureRow label="Gols sofridos/jogo" value={explanation.features.away_as_away?.avg_goals_conceded} />
                    <FeatureRow label="Chutes/jogo" value={explanation.features.away_as_away?.avg_shots} />
                    <FeatureRow label="Escanteios/jogo" value={explanation.features.away_as_away?.avg_corners} />
                    <FeatureRow label="Taxa de vitória (fora)" value={explanation.features.away_as_away?.win_rate} pct />
                    <FeatureRow label="Posse média" value={explanation.features.away_as_away?.avg_possession} suffix="%" />
                  </div>
                </div>
              </div>
              {explanation.features.h2h && explanation.features.h2h.matches_count > 0 && (
                <div className="mt-3 text-xs text-center text-[var(--text-secondary)]">
                  Confronto direto nos últimos {explanation.features.h2h.matches_count} jogos:{" "}
                  {match!.home_team.name} venceu {explanation.features.h2h.home_wins},{" "}
                  {match!.away_team.name} venceu {explanation.features.h2h.away_wins},{" "}
                  {explanation.features.h2h.draws} empate(s) — média de{" "}
                  {explanation.features.h2h.avg_total_goals?.toFixed(1)} gols por jogo
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
