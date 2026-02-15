/**
 * System Statistics type definitions
 * 
 * Type definitions for system-wide statistics data structures.
 * All data is scoped to the requested time range by the backend.
 */

export type TimeRange = 'today' | '7days' | '30days' | 'all';

export interface TotalStats {
  total_runs: number;
  unique_users: number;
  avg_runs_per_user: number;
}

export interface StatusBreakdown {
  [status: string]: number;
}

export interface UserActivity {
  user_id: string;
  run_count: number;
  unique_blueprints: number;
  status_breakdown: StatusBreakdown;
}

export interface BlueprintUsage {
  blueprint_id: string;
  blueprint_name: string;
  run_count: number;
  unique_users: number;
}

export interface TimeSeriesData {
  period: string;
  count: number;
}

export interface SystemStatsResponse {
  total_stats: TotalStats;
  status_breakdown: StatusBreakdown;
  active_users: UserActivity[];
  top_blueprints: BlueprintUsage[];
  time_series?: TimeSeriesData[];
  generated_at: string;
}

