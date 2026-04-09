"use client";

import { useState, useEffect } from "react";
import { Team, PlayerInfo, SquadResponse, getSquad } from "@/lib/api";
import Image from "next/image";

interface Props {
  teams: Team[];
}

const POS_LABELS: Record<string, string> = {
  Goalkeeper: "Goleiro",
  Defender: "Defensor",
  Midfielder: "Meio-campista",
  Attacker: "Atacante",
};

const POS_COLORS: Record<string, string> = {
  Goalkeeper: "var(--accent-yellow)",
  Defender: "var(--accent-blue)",
  Midfielder: "var(--accent-green)",
  Attacker: "var(--accent-red)",
};

function StarterBadge({ lineups, appearances }: { lineups: number; appearances: number }) {
  if (appearances === 0) return <span className="text-[10px] text-[var(--text-secondary)]">Sem jogos</span>;
  const pct = (lineups / appearances) * 100;
  const isStarter = pct >= 60;
  return (
    <span
      className="text-[10px] font-semibold px-1.5 py-0.5 rounded"
      style={{
        backgroundColor: isStarter ? "rgba(34,197,94,0.15)" : "rgba(156,163,175,0.15)",
        color: isStarter ? "var(--accent-green)" : "var(--text-secondary)",
      }}
    >
      {isStarter ? "Titular" : "Reserva"} ({pct.toFixed(0)}%)
    </span>
  );
}

function PlayerCard({ player }: { player: PlayerInfo }) {
  const stats = player.season_stats;
  const posColor = POS_COLORS[player.position || ""] || "var(--text-secondary)";

  return (
    <div className="bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)] p-4 hover:border-[var(--accent-blue)] transition-colors">
      <div className="flex items-start gap-3">
        {/* Foto + número */}
        <div className="relative flex-shrink-0">
          {player.photo ? (
            <Image
              src={player.photo}
              alt={player.name}
              width={48}
              height={48}
              className="rounded-full"
            />
          ) : (
            <div className="w-12 h-12 rounded-full bg-[var(--bg-secondary)] flex items-center justify-center text-lg font-bold">
              {player.number || "?"}
            </div>
          )}
          {player.number && (
            <span className="absolute -bottom-1 -right-1 bg-[var(--bg-secondary)] text-[10px] font-bold rounded-full w-5 h-5 flex items-center justify-center border border-[var(--border-color)]">
              {player.number}
            </span>
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-semibold text-sm truncate">{player.name}</span>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className="text-[10px] font-semibold px-1.5 py-0.5 rounded"
              style={{ backgroundColor: `${posColor}22`, color: posColor }}
            >
              {POS_LABELS[player.position || ""] || player.position || "—"}
            </span>
            {stats && (
              <StarterBadge lineups={stats.lineups} appearances={stats.appearances} />
            )}
            {player.nationality && (
              <span className="text-[10px] text-[var(--text-secondary)]">{player.nationality}</span>
            )}
          </div>
        </div>
      </div>

      {/* Stats */}
      {stats && stats.appearances > 0 && (
        <div className="mt-3 grid grid-cols-4 gap-2 text-center">
          <StatMini label="Jogos" value={stats.appearances} />
          <StatMini label="Gols" value={stats.goals} highlight={stats.goals > 0} />
          <StatMini label="Assist." value={stats.assists} highlight={stats.assists > 0} />
          <StatMini label="Rating" value={stats.rating?.toFixed(1) || "—"} />
          <StatMini label="Min" value={stats.minutes} />
          <StatMini label="🟨" value={stats.yellow_cards} warn={stats.yellow_cards >= 5} />
          <StatMini label="🟥" value={stats.red_cards} warn={stats.red_cards > 0} />
          <StatMini label="Passes" value={stats.passes_key} />
        </div>
      )}
    </div>
  );
}

function StatMini({
  label,
  value,
  highlight,
  warn,
}: {
  label: string;
  value: string | number;
  highlight?: boolean;
  warn?: boolean;
}) {
  return (
    <div>
      <div
        className={`text-sm font-semibold ${
          warn ? "text-[var(--accent-red)]" : highlight ? "text-[var(--accent-green)]" : ""
        }`}
      >
        {value}
      </div>
      <div className="text-[10px] text-[var(--text-secondary)]">{label}</div>
    </div>
  );
}

export default function TeamSquad({ teams }: Props) {
  const [selectedTeam, setSelectedTeam] = useState<number | null>(null);
  const [squad, setSquad] = useState<SquadResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<string>("all");

  useEffect(() => {
    if (!selectedTeam) {
      setSquad(null);
      return;
    }
    setLoading(true);
    getSquad(selectedTeam)
      .then((res) => setSquad(res.data))
      .catch(() => setSquad(null))
      .finally(() => setLoading(false));
  }, [selectedTeam]);

  const positions = ["all", "Goalkeeper", "Defender", "Midfielder", "Attacker"];
  const filteredPlayers = squad?.players.filter(
    (p) => filter === "all" || p.position === filter
  ) || [];

  // Separar titulares e reservas
  const starters = filteredPlayers.filter(
    (p) => p.season_stats && p.season_stats.appearances > 0 && (p.season_stats.lineups / p.season_stats.appearances) >= 0.6
  );
  const subs = filteredPlayers.filter(
    (p) => !p.season_stats || p.season_stats.appearances === 0 || (p.season_stats.lineups / p.season_stats.appearances) < 0.6
  );

  return (
    <div className="space-y-6">
      {/* Seletor de time */}
      <div className="bg-[var(--bg-card)] rounded-xl p-4 border border-[var(--border-color)]">
        <label className="block text-sm font-medium mb-2">Selecione o time</label>
        <select
          value={selectedTeam || ""}
          onChange={(e) => setSelectedTeam(e.target.value ? Number(e.target.value) : null)}
          className="w-full px-3 py-2 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] text-sm"
        >
          <option value="">Escolha um time...</option>
          {teams.map((t) => (
            <option key={t.api_id} value={t.api_id}>{t.name}</option>
          ))}
        </select>
      </div>

      {loading && (
        <p className="text-center text-[var(--text-secondary)] py-8">Carregando elenco...</p>
      )}

      {squad && !loading && (
        <>
          {/* Header do time */}
          <div className="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-color)]">
            <div className="flex items-center gap-4">
              {squad.team.logo && (
                <Image src={squad.team.logo} alt={squad.team.name} width={56} height={56} />
              )}
              <div>
                <h2 className="text-xl font-bold">{squad.team.name}</h2>
                <p className="text-sm text-[var(--text-secondary)]">
                  Temporada {squad.season} — {squad.players.length} jogadores
                </p>
              </div>
            </div>

            {/* Filtro por posição */}
            <div className="flex gap-1 mt-4 flex-wrap">
              {positions.map((pos) => (
                <button
                  key={pos}
                  onClick={() => setFilter(pos)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                    filter === pos
                      ? "bg-[var(--accent-blue)] text-white"
                      : "bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:text-white"
                  }`}
                >
                  {pos === "all" ? "Todos" : POS_LABELS[pos] || pos}
                </button>
              ))}
            </div>
          </div>

          {/* Titulares */}
          {starters.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-3">
                Titulares ({starters.length})
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {starters.map((p) => (
                  <PlayerCard key={p.api_id} player={p} />
                ))}
              </div>
            </div>
          )}

          {/* Reservas */}
          {subs.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-3">
                Reservas ({subs.length})
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {subs.map((p) => (
                  <PlayerCard key={p.api_id} player={p} />
                ))}
              </div>
            </div>
          )}

          {filteredPlayers.length === 0 && (
            <p className="text-center text-[var(--text-secondary)] py-8">
              Nenhum jogador encontrado. Colete os elencos na aba Dados.
            </p>
          )}
        </>
      )}

      {!selectedTeam && !loading && (
        <p className="text-center text-[var(--text-secondary)] py-12">
          Selecione um time para ver o elenco completo com estatísticas.
        </p>
      )}
    </div>
  );
}
