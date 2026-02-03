/**
 * Analytics API client for workflow statistics
 * 
 * NOTE: Uses axios from @/http/axiosAgentConfig which points to /api2 (Multi-Agent Service).
 * Analytics endpoints are in multi-agent/api/flask/endpoints/statistics.py.
 */

import axios from '@/http/axiosAgentConfig';
import type { AnalyticsOverview } from '@/types/analytics';

/**
 * Fetch comprehensive system-wide analytics statistics (workflows, users, blueprints)
 * 
 * This single endpoint returns all analytics data needed for the dashboard:
 * - Total stats (runs, users, avg runs per user)
 * - Status breakdown
 * - Active users by time period (today, 7 days, 30 days)
 * - Top users and blueprints
 * - Time series activity data
 */
export async function fetchAnalyticsOverview(timeRange: 'today' | '7days' | '30days' | 'all' = 'all', userId?: string): Promise<AnalyticsOverview> {
  const params: any = { time_range: timeRange };
  if (userId) {
    params.userId = userId;
  }
  const response = await axios.get<AnalyticsOverview>('/statistics/analytics.overview.get', { params });
  return response.data;
}

