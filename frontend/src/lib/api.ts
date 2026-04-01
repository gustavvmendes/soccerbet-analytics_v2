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

export const getUpcomingMatches = (page = 1) =>
  api.get<{
    matches: MatchData[];
    total: number;
    page: number;
    pages: number;
  }>("/matches/upcoming", { params: { page, per_page: 20 } });

export const getH2H = (homeTeam: number, awayTeam: number) =>
  api.get<{ home_team: Team; away_team: Team; matches: MatchData[] }>(
    "/matches/h2h",
    { params: { home_team: homeTeam, away_team: awayTeam } }
  );

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

export default api;
