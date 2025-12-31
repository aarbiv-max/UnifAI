/**
 * Analytics type definitions
 * 
 * Type definitions for analytics and statistics data structures
 */

export interface TotalStats {
  total_runs: number;
  unique_users: number;
  avg_runs_per_user: number;
}

export interface StatusBreakdown {
  [status: string]: number;
}

export interface StatusBreakdownMap {
  [status: string]: number;
}

export interface UserActivity {
  user_id: string;
  total_runs: number;
  unique_blueprints: number;
  status_breakdown: StatusBreakdownMap;
}

export interface ActiveUser {
  user_id: string;
  recent_runs: number;
  runs_today?: number;
  last_run_id: string;
  status_breakdown: StatusBreakdownMap;
}

export interface TimeStats {
  earliest_run: {
    run_id: string;
    user_id: string;
    timestamp: string;
  } | null;
  latest_run: {
    run_id: string;
    user_id: string;
    timestamp: string;
  } | null;
  time_span_days: number | null;
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

export interface AnalyticsOverview {
  total_stats: TotalStats;
  status_breakdown: StatusBreakdown;
  time_stats: TimeStats;
  active_today: ActiveUser[];
  active_7days: ActiveUser[];
  active_30days: ActiveUser[];
  top_users: UserActivity[];
  top_blueprints: BlueprintUsage[];
  time_series?: TimeSeriesData[];
  generated_at: string;
}

