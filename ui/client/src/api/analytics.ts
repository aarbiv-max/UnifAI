/**
 * Analytics API client for workflow statistics
 * 
 * NOTE: Uses axios from @/http/axiosAgentConfig which points to /api2 (Multi-Agent Service).
 * Analytics endpoints are in multi-agent/api/flask/endpoints/statistics.py.
 */

import axios from '@/http/axiosAgentConfig';

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

/**
 * Fetch comprehensive analytics overview
 */
export async function fetchAnalyticsOverview(timeRange: 'today' | '7days' | '30days' | 'all' = 'all', userId?: string): Promise<AnalyticsOverview> {
  const params: any = { time_range: timeRange };
  if (userId) {
    params.userId = userId;
  }
  const response = await axios.get<AnalyticsOverview>('/statistics/overview', { params });
  return response.data;
}

/**
 * Fetch active users for a specific time period
 * NOTE: This endpoint may not exist yet in the multi-agent service
 */
export async function fetchActiveUsers(days: number = 7): Promise<{ active_users: ActiveUser[], count: number, days: number }> {
  const response = await axios.get<{ active_users: ActiveUser[], count: number, days: number }>(
    '/statistics/users/active',
    { params: { days } }
  );
  return response.data;
}

/**
 * Fetch user activity breakdown
 * NOTE: This endpoint may not exist yet in the multi-agent service
 */
export async function fetchUserActivity(limit: number = 15): Promise<{ user_activity: UserActivity[], count: number }> {
  const response = await axios.get<{ user_activity: UserActivity[], count: number }>(
    '/statistics/users/activity',
    { params: { limit } }
  );
  return response.data;
}

/**
 * Fetch blueprint usage statistics
 * NOTE: This endpoint may not exist yet in the multi-agent service
 */
export async function fetchBlueprintUsage(limit: number = 10): Promise<{ blueprint_usage: BlueprintUsage[], count: number }> {
  const response = await axios.get<{ blueprint_usage: BlueprintUsage[], count: number }>(
    '/statistics/blueprints/usage',
    { params: { limit } }
  );
  return response.data;
}

