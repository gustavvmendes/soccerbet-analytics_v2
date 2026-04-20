import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:5000/api",
  timeout: 300000,
});

export interface Team {
  id: number;
  api_id: number;
  name: string;
  logo: string | null;
  country: string | null;
}

export interface PredictionResult {
  home_team: Team;
  away_team: Team;
  lambda_home: number;
  lambda_away: number;
  home_win_prob: number;
  draw_prob: number;
  away_win_prob: number;
  over_05: number;
  over_15: number;
  over_25: number;
  over_35: number;
  btts_prob: number;
  most_likely_score: { home: number; away: number };
  score_matrix: number[][];
  confidence: string;
  xgb_predictions: {
    home_corners: number;
    away_corners: number;
    home_cards: number;
    away_cards: number;
    home_possession: number;
    away_possession: number;
    home_shots: number;
    away_shots: number;
  };
}

export interface MatchData {
  id: number;
  api_id: number;
  date: string;
  round: string | null;
  status: string;
  home_team: Team;
  away_team: Team;
  home_goals: number;
  away_goals: number;
  statistics: Record<string, number> | null;
}

export interface DataStatus {
  total_matches: number;
  total_teams: number;
  seasons: number[];
  models_trained: boolean;
}

export const getTeams = () => api.get<Team[]>("/matches/teams");

export const getMatchHistory = (params: {
  page?: number;
  per_page?: number;
  team_id?: number;
  season?: number;
}) =>
  api.get<{
    matches: MatchData[];
    total: number;
    page: number;
    pages: number;
  }>("/matches/history", { params });

export const getUpcomingMatches = (page = 1, teamId?: number) =>
  api.get<{
    matches: MatchData[];
    total: number;
    page: number;
    pages: number;
  }>("/matches/upcoming", { params: { page, per_page: 20, ...(teamId ? { team_id: teamId } : {}) } });

export const getH2H = (homeTeam: number, awayTeam: number) =>
  api.get<{ home_team: Team; away_team: Team; matches: MatchData[] }>(
    "/matches/h2h",
    { params: { home_team: homeTeam, away_team: awayTeam } }
  );

export interface MatchDetails {
  match: MatchData;
  prediction: PredictionResult | null;
}

// ── Novos tipos ──────────────────────────────────────

export interface PlayerInfo {
  id: number;
  api_id: number;
  name: string;
  firstname: string | null;
  lastname: string | null;
  age: number | null;
  nationality: string | null;
  height: string | null;
  weight: string | null;
  photo: string | null;
  position: string | null;
  number: number | null;
  team_api_id: number;
  season_stats: PlayerSeasonStats | null;
}

export interface PlayerSeasonStats {
  player_api_id: number;
  team_api_id: number;
  season: number;
  appearances: number;
  lineups: number;
  minutes: number;
  rating: number | null;
  goals: number;
  assists: number;
  yellow_cards: number;
  red_cards: number;
  shots_total: number;
  shots_on: number;
  passes_total: number;
  passes_key: number;
  passes_accuracy: number | null;
  tackles: number;
  interceptions: number;
  duels_total: number;
  duels_won: number;
  dribbles_attempts: number;
  dribbles_success: number;
  fouls_drawn: number;
  fouls_committed: number;
}

export interface SquadResponse {
  team: Team;
  players: PlayerInfo[];
  season: number;
}

export interface LineupTeam {
  team: Team;
  formation: string;
  starters: LineupPlayer[];
  substitutes: LineupPlayer[];
}

export interface LineupPlayer {
  team_api_id: number;
  formation: string;
  player_api_id: number;
  player_name: string;
  player_number: number | null;
  player_pos: string | null;
  player_grid: string | null;
  is_starter: boolean;
}

export interface InjuryTeam {
  team: Team;
  injuries: InjuryEntry[];
}

export interface InjuryEntry {
  team_api_id: number;
  player_api_id: number;
  player_name: string;
  player_photo: string | null;
  type: string;
  reason: string;
}

export interface OddsData {
  bookmaker: string;
  match_winner: { home: number | null; draw: number | null; away: number | null };
  match_winner_probs: { home: number | null; draw: number | null; away: number | null };
  over_under_25: { over: number | null; under: number | null };
  btts: { yes: number | null; no: number | null };
  double_chance: { home_draw: number | null; draw_away: number | null; home_away: number | null };
}

export interface ExplanationDC {
  home_attack: number;
  home_defense: number;
  away_attack: number;
  away_defense: number;
  home_advantage: number;
  home_advantage_pct: number;
  league_avg_attack: number;
  league_avg_defense: number;
  home_attack_rank: number;
  home_defense_rank: number;
  away_attack_rank: number;
  away_defense_rank: number;
  total_teams: number;
  lambda_home: number;
  lambda_away: number;
  formula_home: string;
  formula_away: string;
}

export interface ExplanationFeatures {
  home_form: Record<string, number>;
  home_as_home: Record<string, number>;
  away_form: Record<string, number>;
  away_as_away: Record<string, number>;
  h2h: Record<string, number>;
}

export interface KeyFactor {
  type: string;
  text: string;
}

export interface ExplanationData {
  dixon_coles: ExplanationDC | null;
  features: ExplanationFeatures | null;
  key_factors: KeyFactor[];
}

export const getMatchDetails = (matchId: number) =>
  api.get<MatchDetails>(`/matches/${matchId}/details`);

export const predict = (homeTeamApiId: number, awayTeamApiId: number) =>
  api.post<PredictionResult>("/predictions/predict", {
    home_team_api_id: homeTeamApiId,
    away_team_api_id: awayTeamApiId,
  });

export const getPredictionHistory = (page = 1) =>
  api.get<{
    predictions: any[];
    total: number;
    page: number;
    pages: number;
  }>("/predictions/history", { params: { page } });

export const getMetrics = () => api.get("/predictions/metrics");

export const collectData = (season: number) =>
  api.post("/data/collect", { season });

export const collectMultipleSeasons = (seasons: number[]) =>
  api.post("/data/collect/multiple", { seasons });

export const trainModels = (seasons: number[]) =>
  api.post("/data/train", { seasons });

export const getDataStatus = () => api.get<DataStatus>("/data/status");

// ── Novas API functions ──────────────────────────────

export const getSquad = (teamApiId: number, season = 2026) =>
  api.get<SquadResponse>(`/matches/squad/${teamApiId}`, { params: { season } });

export const getMatchLineups = (matchId: number) =>
  api.get<LineupTeam[]>(`/matches/${matchId}/lineups`);

export const getMatchInjuries = (matchId: number) =>
  api.get<InjuryTeam[]>(`/matches/${matchId}/injuries`);

export const getMatchOdds = (matchId: number) =>
  api.get<OddsData | null>(`/matches/${matchId}/odds`);

export const getMatchExplanation = (matchId: number) =>
  api.get<ExplanationData>(`/matches/${matchId}/explanation`);

export const collectSquads = (season: number) =>
  api.post("/data/collect/squads", { season });

export const collectLineups = (season: number) =>
  api.post("/data/collect/lineups", { season });

export const collectOdds = (season: number) =>
  api.post("/data/collect/odds", { season });

export const collectInjuries = (season: number) =>
  api.post("/data/collect/injuries", { season });

// ── Player match prediction ─────────────────────────

export interface PlayerPredictionStats {
  goals: number;
  goal_probability: number;
  shots: number;
  assists: number;
  assist_probability: number;
  key_passes: number;
  tackles: number;
  interceptions: number;
  dribbles: number;
  fouls_committed: number;
  yellow_card_prob: number;
  red_card_prob: number;
  estimated_rating: number | null;
}

export interface PlayerContribution {
  goal_share: number;
  shot_share: number;
  assist_share: number;
  card_share: number;
}

export interface PlayerPredictionExplanation {
  type: string;
  text: string;
}

export interface PlayerMatchPrediction {
  player: PlayerInfo;
  season_stats: PlayerSeasonStats;
  match: MatchData;
  is_home: boolean;
  starter_probability: number;
  estimated_minutes: number;
  predictions: PlayerPredictionStats;
  contribution: PlayerContribution;
  team_prediction: {
    team_lambda: number;
    team_shots: number;
    team_corners: number;
    team_cards: number;
  };
  explanations: PlayerPredictionExplanation[];
}

export const getPlayerMatchPrediction = (matchId: number, playerApiId: number) =>
  api.get<PlayerMatchPrediction>(`/matches/${matchId}/player-prediction/${playerApiId}`);

// ── Live match analysis ─────────────────────────────

export interface LiveTeam {
  api_id: number;
  name: string;
  logo: string | null;
}

export interface LiveScore {
  home: number;
  away: number;
  halftime: { home: number | null; away: number | null };
}

export interface LiveEvent {
  time_elapsed: number | null;
  time_extra: number | null;
  team_id: number;
  team_name: string;
  player_name: string | null;
  assist_name: string | null;
  type: string;
  detail: string;
  comments: string | null;
}

export interface LiveProbabilities {
  home_win_prob: number;
  draw_prob: number;
  away_win_prob: number;
  lambda_home_remaining: number;
  lambda_away_remaining: number;
  over_under: Record<string, number>;
  home_xg: number;
  away_xg: number;
  next_goal: { home: number; away: number; no_more_goals: number };
  btts_prob: number;
  most_likely_final_score: { home: number; away: number };
  modifiers: {
    home_red_cards: number;
    away_red_cards: number;
    home_performance: number;
    away_performance: number;
    remaining_fraction: number;
  };
}

export interface LiveMomentum {
  home: number;
  away: number;
  trend: string;
  home_activity: { shots: number; corners: number; dangerous_attacks: number };
  away_activity: { shots: number; corners: number; dangerous_attacks: number };
}

export interface LiveInsight {
  type: string;
  text: string;
  severity: string;
}

export interface LiveMatchAnalysis {
  fixture_id: number;
  status: string;
  elapsed: number;
  home_team: LiveTeam;
  away_team: LiveTeam;
  score: LiveScore;
  statistics: Record<string, number>;
  events: LiveEvent[];
  live_probabilities: LiveProbabilities;
  pre_match_probabilities: {
    home_win: number | null;
    draw: number | null;
    away_win: number | null;
  };
  momentum: LiveMomentum;
  insights: LiveInsight[];
  snapshot_count: number;
}

export interface LiveMatchesResponse {
  matches: LiveMatchAnalysis[];
  last_updated: string | null;
  match_count?: number;
  status?: string;
}

export const getLiveMatches = () =>
  api.get<LiveMatchesResponse>("/live/matches");

export const getLiveMatchDetail = (fixtureId: number) =>
  api.get<LiveMatchAnalysis>(`/live/match/${fixtureId}`);

export const getLiveSnapshots = (fixtureId: number) =>
  api.get<{ fixture_id: number; snapshots: any[]; count: number }>(
    `/live/match/${fixtureId}/snapshots`
  );

export default api;
