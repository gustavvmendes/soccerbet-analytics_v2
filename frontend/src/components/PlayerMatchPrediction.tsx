"use client";

import { useState, useEffect } from "react";
import {
  PlayerMatchPrediction as PlayerMatchPredictionData,
  getPlayerMatchPrediction,
} from "@/lib/api";
import Image from "next/image";

interface Props {
  matchId: number;
  playerApiId: number;
  onBack: () => void;
}

function PredStatCard({
  label,
  value,
  subtitle,
  color,
  large,
}: {
  label: string;
  value: string;
  subtitle?: string;
  color?: string;
  large?: boolean;
}) {
  return (
    <div className="bg-[var(--bg-secondary)] rounded-lg p-3 text-center">
      <div
        className={`font-bold ${large ? "text-2xl" : "text-lg"}`}
        style={color ? { color } : {}}
      >
        {value}
      </div>
      <div className="text-[10px] text-[var(--text-secondary)] mt-0.5">{label}</div>
      {subtitle && (
        <div className="text-[9px] text-[var(--text-secondary)] mt-0.5">{subtitle}</div>
      )}
    </div>
  );
}

function ProbRing({ prob, size = 56, label }: { prob: number; size?: number; label: string }) {
  const r = (size - 6) / 2;
  const circ = 2 * Math.PI * r;
  const filled = (prob / 100) * circ;
  const color =
    prob >= 50 ? "var(--accent-green)" : prob >= 25 ? "var(--accent-yellow)" : "var(--accent-red)";

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} className="block">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--bg-secondary)"
          strokeWidth={4}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={4}
          strokeDasharray={`${filled} ${circ - filled}`}
          strokeDashoffset={circ / 4}
          strokeLinecap="round"
          className="transition-all duration-700"
        />
        <text
          x="50%"
          y="50%"
          textAnchor="middle"
          dy=".35em"
          className="text-xs font-bold"
          fill="currentColor"
        >
          {prob.toFixed(0)}%
        </text>
      </svg>
      <span className="text-[10px] text-[var(--text-secondary)] mt-1">{label}</span>
    </div>
  );
}

export default function PlayerMatchPrediction({ matchId, playerApiId, onBack }: Props) {
  const [data, setData] = useState<PlayerMatchPredictionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getPlayerMatchPrediction(matchId, playerApiId)
      .then((res) => setData(res.data))
      .catch((err) => setError(err.response?.data?.error || "Erro ao carregar predição"))
      .finally(() => setLoading(false));
  }, [matchId, playerApiId]);

  if (loading) {
    return <p className="p-6 text-center text-[var(--text-secondary)]">Carregando predição do jogador...</p>;
  }

  if (error || !data) {
    return (
      <div className="text-center p-6">
        <p className="text-[var(--accent-red)] mb-4">{error || "Dados não encontrados"}</p>
        <button onClick={onBack} className="text-[var(--accent-blue)] text-sm underline">
          ← Voltar
        </button>
      </div>
    );
  }

  const { player, season_stats: ss, predictions: pred, contribution: contrib, team_prediction: tp, explanations } = data;
  const posLabels: Record<string, string> = {
    Goalkeeper: "Goleiro",
    Defender: "Defensor",
    Midfielder: "Meio-campista",
    Attacker: "Atacante",
  };

  return (
    <div className="space-y-6">
      {/* Voltar */}
      <button
        onClick={onBack}
        className="text-sm text-[var(--accent-blue)] hover:underline flex items-center gap-1"
      >
        ← Voltar para a partida
      </button>

      {/* Cabeçalho do jogador */}
      <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)]">
        <div className="flex items-center gap-4">
          {player.photo ? (
            <Image src={player.photo} alt={player.name} width={72} height={72} className="rounded-full" />
          ) : (
            <div className="w-[72px] h-[72px] rounded-full bg-[var(--bg-secondary)] flex items-center justify-center text-2xl font-bold">
              {player.number || "?"}
            </div>
          )}
          <div>
            <h2 className="text-2xl font-bold">{player.name}</h2>
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              {player.number && (
                <span className="text-sm bg-[var(--bg-secondary)] px-2 py-0.5 rounded font-medium">
                  #{player.number}
                </span>
              )}
              <span className="text-sm text-[var(--accent-blue)]">
                {posLabels[player.position || ""] || player.position}
              </span>
              {player.nationality && (
                <span className="text-xs text-[var(--text-secondary)]">{player.nationality}</span>
              )}
              <span
                className="text-xs font-semibold px-2 py-0.5 rounded"
                style={{
                  backgroundColor: data.starter_probability >= 60 ? "rgba(34,197,94,0.15)" : "rgba(156,163,175,0.15)",
                  color: data.starter_probability >= 60 ? "var(--accent-green)" : "var(--text-secondary)",
                }}
              >
                {data.starter_probability >= 60 ? "Provável Titular" : "Provável Reserva"} ({data.starter_probability}%)
              </span>
            </div>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              {data.match.home_team.name} vs {data.match.away_team.name} — {data.is_home ? "Jogando em casa" : "Jogando fora"}
            </p>
          </div>
        </div>
      </div>

      {/* Probabilidades principais */}
      <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)]">
        <h3 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-4">
          Probabilidades para esta Partida
        </h3>
        <div className="flex justify-center gap-8 flex-wrap">
          <ProbRing prob={pred.goal_probability} label="Marcar Gol" size={80} />
          <ProbRing prob={pred.assist_probability} label="Dar Assistência" size={80} />
          <ProbRing prob={pred.yellow_card_prob} label="Cartão Amarelo" size={80} />
          <ProbRing prob={pred.red_card_prob} label="Cartão Vermelho" size={80} />
        </div>
      </div>

      {/* Estatísticas previstas */}
      <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)]">
        <h3 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-4">
          Estatísticas Previstas
        </h3>
        <div className="grid grid-cols-3 md:grid-cols-5 gap-3">
          <PredStatCard
            label="Gols Esperados"
            value={pred.goals.toFixed(3)}
            subtitle={`${pred.goal_probability}% de marcar`}
            color="var(--accent-green)"
            large
          />
          <PredStatCard
            label="Chutes"
            value={pred.shots.toFixed(1)}
            subtitle={`${contrib.shot_share}% dos chutes do time`}
          />
          <PredStatCard
            label="Assistências Esp."
            value={pred.assists.toFixed(3)}
            subtitle={`${pred.assist_probability}% de assistir`}
          />
          <PredStatCard
            label="Passes Decisivos"
            value={pred.key_passes.toFixed(1)}
          />
          <PredStatCard
            label="Desarmes"
            value={pred.tackles.toFixed(1)}
          />
          <PredStatCard
            label="Interceptações"
            value={pred.interceptions.toFixed(1)}
          />
          <PredStatCard
            label="Dribles"
            value={pred.dribbles.toFixed(1)}
          />
          <PredStatCard
            label="Faltas Cometidas"
            value={pred.fouls_committed.toFixed(1)}
          />
          <PredStatCard
            label="Minutos Est."
            value={`${data.estimated_minutes}`}
          />
          {pred.estimated_rating && (
            <PredStatCard
              label="Rating Estimado"
              value={pred.estimated_rating.toFixed(2)}
              color={pred.estimated_rating >= 7 ? "var(--accent-green)" : pred.estimated_rating >= 6.5 ? "var(--accent-yellow)" : "var(--accent-red)"}
            />
          )}
        </div>
      </div>

      {/* Contribuição no time */}
      <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)]">
        <h3 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-4">
          Contribuição no Time (temporada)
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "Gols do Time", share: contrib.goal_share, teamVal: tp.team_lambda, unit: "xG" },
            { label: "Chutes do Time", share: contrib.shot_share, teamVal: tp.team_shots, unit: "chutes" },
            { label: "Assistências do Time", share: contrib.assist_share, teamVal: tp.team_lambda, unit: "xG" },
            { label: "Cartões do Time", share: contrib.card_share, teamVal: tp.team_cards, unit: "cartões" },
          ].map((item) => (
            <div key={item.label} className="text-center">
              <div className="text-lg font-bold text-[var(--accent-blue)]">{item.share}%</div>
              <div className="text-xs text-[var(--text-secondary)]">{item.label}</div>
              <div className="text-[10px] text-[var(--text-secondary)] mt-1">
                Time prevê {item.teamVal.toFixed(1)} {item.unit}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Comparação: temporada vs predição */}
      <div className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-color)] overflow-hidden">
        <div className="p-4 border-b border-[var(--border-color)]">
          <h3 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
            Média na Temporada vs Predição deste Jogo
          </h3>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border-color)] text-[var(--text-secondary)]">
              <th className="py-2 px-3 text-left font-medium">Estatística</th>
              <th className="py-2 px-3 text-center font-medium">Média/jogo</th>
              <th className="py-2 px-3 text-center font-medium">Predição</th>
            </tr>
          </thead>
          <tbody>
            {[
              { label: "Gols", avg: ss.goals / ss.appearances, pred: pred.goals },
              { label: "Chutes", avg: ss.shots_total / ss.appearances, pred: pred.shots },
              { label: "Assistências", avg: ss.assists / ss.appearances, pred: pred.assists },
              { label: "Passes Decisivos", avg: ss.passes_key / ss.appearances, pred: pred.key_passes },
              { label: "Desarmes", avg: ss.tackles / ss.appearances, pred: pred.tackles },
              { label: "Interceptações", avg: ss.interceptions / ss.appearances, pred: pred.interceptions },
              { label: "Dribles", avg: ss.dribbles_success / ss.appearances, pred: pred.dribbles },
              { label: "Faltas", avg: ss.fouls_committed / ss.appearances, pred: pred.fouls_committed },
            ].map((row) => {
              const diff = row.pred - row.avg;
              const diffColor = diff > 0.05 ? "text-[var(--accent-green)]" : diff < -0.05 ? "text-[var(--accent-red)]" : "";
              return (
                <tr key={row.label} className="border-b border-[var(--border-color)]">
                  <td className="py-2 px-3">{row.label}</td>
                  <td className="py-2 px-3 text-center">{row.avg.toFixed(2)}</td>
                  <td className={`py-2 px-3 text-center font-medium ${diffColor}`}>
                    {row.pred.toFixed(2)}
                    {Math.abs(diff) > 0.05 && (
                      <span className="text-[10px] ml-1">
                        ({diff > 0 ? "+" : ""}{diff.toFixed(2)})
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Explicações */}
      {explanations.length > 0 && (
        <div className="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)]">
          <h3 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-4">
            Por que esses valores?
          </h3>
          <div className="space-y-2">
            {explanations.map((exp, i) => (
              <div
                key={i}
                className="flex items-start gap-2 text-sm py-2 px-3 rounded"
                style={{
                  backgroundColor:
                    exp.type === "positive" ? "rgba(34,197,94,0.08)"
                    : exp.type === "negative" ? "rgba(239,68,68,0.08)"
                    : exp.type === "methodology" ? "rgba(59,130,246,0.08)"
                    : exp.type === "context" ? "rgba(234,179,8,0.08)"
                    : "rgba(156,163,175,0.06)",
                }}
              >
                <span className="flex-shrink-0 mt-0.5">
                  {exp.type === "positive" ? "✅"
                  : exp.type === "negative" ? "⚠️"
                  : exp.type === "methodology" ? "🔬"
                  : exp.type === "context" ? "⚽"
                  : "ℹ️"}
                </span>
                <span>{exp.text}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
