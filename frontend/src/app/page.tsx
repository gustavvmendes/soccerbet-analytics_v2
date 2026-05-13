"use client";

import { useState, useEffect } from "react";
import DataManager from "@/components/DataManager";
import MatchHistory from "@/components/MatchHistory";
import UpcomingMatches from "@/components/UpcomingMatches";
import TeamSquad from "@/components/TeamSquad";
import LiveMatches from "@/components/LiveMatches";
import { Team, getTeams } from "@/lib/api";

type Tab = "live" | "upcoming" | "history" | "squads" | "data";

export default function Home() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>("upcoming");

  useEffect(() => {
    getTeams()
      .then((res) => setTeams(res.data))
      .catch(() => {});
  }, []);

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
      <nav className="flex gap-1 mb-8 bg-[var(--bg-secondary)] rounded-lg p-1 max-w-lg mx-auto">
        {([
          ["live", "Ao Vivo"],
          ["upcoming", "Próximos Jogos"],
          ["history", "Histórico"],
          ["squads", "Elencos"],
          // ["data", "Dados"],
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

      {/* Tab: Ao Vivo */}
      {activeTab === "live" && <LiveMatches />}

      {/* Tab: Próximos Jogos */}
      {activeTab === "upcoming" && <UpcomingMatches teams={teams} />}

      {/* Tab: Histórico */}
      {activeTab === "history" && <MatchHistory teams={teams} />}

      {/* Tab: Elencos */}
      {activeTab === "squads" && <TeamSquad teams={teams} />}

      {/* Tab: Dados (COMENTADO) */}
      {/* {activeTab === "data" && <DataManager />} */}
    </main>
  );
}
