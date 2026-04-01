"use client";

import { PredictionResult } from "@/lib/api";
import Image from "next/image";

interface Props {
  prediction: PredictionResult;
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

export default function PredictionDisplay({ prediction }: Props) {
  const p = prediction;
  const xgb = p.xgb_predictions;

  const confidenceColor =
    p.confidence === "alta"
      ? "var(--accent-green)"
      : p.confidence === "media"
      ? "var(--accent-yellow)"
      : "var(--accent-red)";

  return (
    <div className="space-y-6">
      {/* Header com times e placar mais provável */}
      <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)]">
        <div className="flex items-center justify-between mb-4">
          <span
            className="text-xs font-semibold px-2 py-1 rounded"
            style={{ backgroundColor: confidenceColor, color: "#fff" }}
          >
            Confiança {p.confidence}
          </span>
          <span className="text-xs text-[var(--text-secondary)]">
            Dixon-Coles + XGBoost
          </span>
        </div>

        <div className="grid grid-cols-3 items-center text-center gap-4">
          <div className="flex flex-col items-center gap-2">
            {p.home_team.logo && (
              <Image
                src={p.home_team.logo}
                alt={p.home_team.name}
                width={64}
                height={64}
              />
            )}
            <span className="font-semibold text-sm">{p.home_team.name}</span>
          </div>

          <div>
            <div className="text-4xl font-bold">
              {p.most_likely_score.home} - {p.most_likely_score.away}
            </div>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Placar mais provável
            </p>
          </div>

          <div className="flex flex-col items-center gap-2">
            {p.away_team.logo && (
              <Image
                src={p.away_team.logo}
                alt={p.away_team.name}
                width={64}
                height={64}
              />
            )}
            <span className="font-semibold text-sm">{p.away_team.name}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Resultado */}
        <div className="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)]">
          <h3 className="text-sm font-semibold mb-4 text-[var(--text-secondary)] uppercase tracking-wider">
            Resultado
          </h3>
          <div className="space-y-3">
            <ProbBar
              label={`Vitória ${p.home_team.name}`}
              value={p.home_win_prob}
              color="var(--accent-blue)"
            />
            <ProbBar
              label="Empate"
              value={p.draw_prob}
              color="var(--accent-yellow)"
            />
            <ProbBar
              label={`Vitória ${p.away_team.name}`}
              value={p.away_win_prob}
              color="var(--accent-red)"
            />
          </div>
        </div>

        {/* Over/Under + BTTS */}
        <div className="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)]">
          <h3 className="text-sm font-semibold mb-4 text-[var(--text-secondary)] uppercase tracking-wider">
            Over/Under & BTTS
          </h3>
          <div className="space-y-3">
            <ProbBar
              label="Over 0.5"
              value={p.over_05}
              color="var(--accent-green)"
            />
            <ProbBar
              label="Over 1.5"
              value={p.over_15}
              color="var(--accent-green)"
            />
            <ProbBar
              label="Over 2.5"
              value={p.over_25}
              color="var(--accent-green)"
            />
            <ProbBar
              label="Over 3.5"
              value={p.over_35}
              color="var(--accent-green)"
            />
            <div className="border-t border-[var(--border-color)] my-2" />
            <ProbBar
              label="Ambas Marcam (BTTS)"
              value={p.btts_prob}
              color="var(--accent-blue)"
            />
          </div>
        </div>

        {/* Gols esperados */}
        <div className="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)]">
          <h3 className="text-sm font-semibold mb-4 text-[var(--text-secondary)] uppercase tracking-wider">
            Gols Esperados (λ)
          </h3>
          <div className="grid grid-cols-2 text-center gap-4">
            <div>
              <div className="text-3xl font-bold text-[var(--accent-blue)]">
                {p.lambda_home.toFixed(2)}
              </div>
              <p className="text-xs text-[var(--text-secondary)] mt-1">
                {p.home_team.name}
              </p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[var(--accent-red)]">
                {p.lambda_away.toFixed(2)}
              </div>
              <p className="text-xs text-[var(--text-secondary)] mt-1">
                {p.away_team.name}
              </p>
            </div>
          </div>
        </div>

        {/* Estatísticas XGBoost */}
        {xgb && (
          <div className="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)]">
            <h3 className="text-sm font-semibold mb-4 text-[var(--text-secondary)] uppercase tracking-wider">
              Estatísticas Previstas
            </h3>
            <div className="space-y-3">
              <StatRow
                label="Posse de Bola (%)"
                home={xgb.home_possession}
                away={xgb.away_possession}
              />
              <StatRow
                label="Chutes"
                home={xgb.home_shots}
                away={xgb.away_shots}
              />
              <StatRow
                label="Escanteios"
                home={xgb.home_corners}
                away={xgb.away_corners}
              />
              <StatRow
                label="Cartões"
                home={xgb.home_cards}
                away={xgb.away_cards}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
