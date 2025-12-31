/**
 * Analytics API client for workflow statistics
 * 
 * NOTE: Uses axios from @/http/axiosAgentConfig which points to /api2 (Multi-Agent Service).
 * Analytics endpoints are in multi-agent/api/flask/endpoints/statistics.py.
 */

import axios from '@/http/axiosAgentConfig';
import type {
  AnalyticsOverview,
  ActiveUser,
  UserActivity,
  BlueprintUsage,
} from '@/types/analytics';

/**
 * Fetch comprehensive system-wide analytics statistics (workflows, users, blueprints)
 */
export async function fetchAnalyticsOverview(timeRange: 'today' | '7days' | '30days' | 'all' = 'all', userId?: string): Promise<AnalyticsOverview> {
  const params: any = { time_range: timeRange };
  if (userId) {
    params.userId = userId;
  }
  const response = await axios.get<AnalyticsOverview>('/statistics/analytics', { params });
  return response.data;
}


export async function fetchActiveUsers(days: number = 7): Promise<{ active_users: ActiveUser[], count: number, days: number }> {
  const response = await axios.get<{ active_users: ActiveUser[], count: number, days: number }>(
    '/statistics/users/active',
    { params: { days } }
  );
  return response.data;
}


export async function fetchUserActivity(limit: number = 15): Promise<{ user_activity: UserActivity[], count: number }> {
  const response = await axios.get<{ user_activity: UserActivity[], count: number }>(
    '/statistics/users/activity',
    { params: { limit } }
  );
  return response.data;
}


export async function fetchBlueprintUsage(limit: number = 10): Promise<{ blueprint_usage: BlueprintUsage[], count: number }> {
  const response = await axios.get<{ blueprint_usage: BlueprintUsage[], count: number }>(
    '/statistics/blueprints/usage',
    { params: { limit } }
  );
  return response.data;
}

