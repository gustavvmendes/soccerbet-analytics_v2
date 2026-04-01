"use client";

import { useState } from "react";
import { Team } from "@/lib/api";
import Image from "next/image";

interface Props {
  label: string;
  teams: Team[];
  selected: Team | null;
  onSelect: (team: Team) => void;
  excludeId?: number;
}

export default function TeamSelector({
  label,
  teams,
  selected,
  onSelect,
  excludeId,
}: Props) {
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);

  const filtered = teams.filter(
    (t) =>
      t.api_id !== excludeId &&
      t.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="relative">
      <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
        {label}
      </label>

      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 p-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg text-left hover:border-[var(--accent-blue)] transition-colors"
      >
        {selected ? (
          <>
            {selected.logo && (
              <Image
                src={selected.logo}
                alt={selected.name}
                width={28}
                height={28}
                className="rounded"
              />
            )}
            <span>{selected.name}</span>
          </>
        ) : (
          <span className="text-[var(--text-secondary)]">
            Selecionar time...
          </span>
        )}
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg shadow-xl max-h-64 overflow-hidden">
          <div className="p-2">
            <input
              type="text"
              placeholder="Buscar time..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full p-2 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded text-sm focus:outline-none focus:border-[var(--accent-blue)]"
              autoFocus
            />
          </div>
          <ul className="max-h-48 overflow-y-auto">
            {filtered.map((team) => (
              <li key={team.api_id}>
                <button
                  onClick={() => {
                    onSelect(team);
                    setOpen(false);
                    setSearch("");
                  }}
                  className="w-full flex items-center gap-3 px-3 py-2 hover:bg-[var(--bg-card)] text-sm text-left transition-colors"
                >
                  {team.logo && (
                    <Image
                      src={team.logo}
                      alt={team.name}
                      width={24}
                      height={24}
                      className="rounded"
                    />
                  )}
                  <span>{team.name}</span>
                </button>
              </li>
            ))}
            {filtered.length === 0 && (
              <li className="px-3 py-2 text-sm text-[var(--text-secondary)]">
                Nenhum time encontrado
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
