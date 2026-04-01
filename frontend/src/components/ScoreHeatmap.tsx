"use client";

interface Props {
  matrix: number[][];
  homeTeam: string;
  awayTeam: string;
}

export default function ScoreHeatmap({ matrix, homeTeam, awayTeam }: Props) {
  if (!matrix || matrix.length === 0) return null;

  const maxGoals = Math.min(matrix.length, 6);
  const sliced = matrix.slice(0, maxGoals).map((row) => row.slice(0, maxGoals));

  const maxProb = Math.max(...sliced.flat());

  const getColor = (value: number) => {
    const intensity = value / maxProb;
    const r = Math.round(59 + intensity * (16 - 59));
    const g = Math.round(130 + intensity * (185 - 130));
    const b = Math.round(246 + intensity * (129 - 246));
    return `rgb(${r}, ${g}, ${b})`;
  };

  return (
    <div className="bg-[var(--bg-card)] rounded-xl p-6 border border-[var(--border-color)]">
      <h3 className="text-sm font-semibold mb-4 text-[var(--text-secondary)] uppercase tracking-wider">
        Matriz de Probabilidade de Placares
      </h3>

      <div className="overflow-x-auto">
        <table className="mx-auto">
          <thead>
            <tr>
              <th className="p-2 text-xs text-[var(--text-secondary)]">
                {homeTeam} \ {awayTeam}
              </th>
              {Array.from({ length: maxGoals }, (_, i) => (
                <th
                  key={i}
                  className="p-2 text-xs text-center text-[var(--text-secondary)] font-normal"
                >
                  {i}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sliced.map((row, i) => (
              <tr key={i}>
                <td className="p-2 text-xs text-[var(--text-secondary)] text-right font-normal">
                  {i}
                </td>
                {row.map((prob, j) => (
                  <td key={j} className="p-1">
                    <div
                      className="w-14 h-10 flex items-center justify-center rounded text-xs font-semibold transition-colors"
                      style={{
                        backgroundColor: getColor(prob),
                        color: prob / maxProb > 0.5 ? "#fff" : "var(--text-primary)",
                      }}
                    >
                      {(prob * 100).toFixed(1)}%
                    </div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-[var(--text-secondary)] text-center mt-3">
        Cada célula mostra a probabilidade do placar exato (linha = gols{" "}
        {homeTeam}, coluna = gols {awayTeam})
      </p>
    </div>
  );
}
