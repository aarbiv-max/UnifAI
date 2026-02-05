/**
 * Analytics Helper Utilities
 * 
 * Shared functions for analytics data transformations and calculations
 */

import type { StatusBreakdown, UserActivity, ActiveUser } from '@/types/systemStats';

interface FilteredStats {
  total_runs: number;
  unique_users: number;
  avg_runs_per_user: number;
}

// Union type for users that can have different run count fields
type UserWithRuns = UserActivity | ActiveUser;

/**
 * Calculate status breakdown from array of users
 */
export function calculateStatusBreakdown(users: UserWithRuns[]): StatusBreakdown {
  const statusBreakdown: StatusBreakdown = {};
  users.forEach(user => {
    Object.entries(user.status_breakdown || {}).forEach(([status, count]) => {
      statusBreakdown[status] = (statusBreakdown[status] || 0) + count;
    });
  });
  return statusBreakdown;
}

/**
 * Calculate total stats from user array
 */
export function calculateStats(users: UserWithRuns[], runsKey: 'total_runs' | 'recent_runs' | 'runs_today'): FilteredStats {
  const totalRuns = users.reduce((sum, u) => {
    const user = u as any; // Type assertion needed due to union type with different field names
    return sum + (user[runsKey] || 0);
  }, 0);
  const uniqueUsers = users.length;
  
  return {
    total_runs: totalRuns,
    unique_users: uniqueUsers,
    avg_runs_per_user: uniqueUsers > 0 ? totalRuns / uniqueUsers : 0
  };
}

/**
 * Map users to top_users format
 */
export function mapToTopUsers(users: UserWithRuns[], runsKey: 'total_runs' | 'recent_runs' | 'runs_today') {
  return users.map(u => {
    const user = u as any; // Type assertion needed due to union type with different field names
    return {
      user_id: u.user_id,
      total_runs: user[runsKey] || 0,
      unique_blueprints: 'unique_blueprints' in u ? u.unique_blueprints : 0,
      status_breakdown: u.status_breakdown || {}
    };
  });
}

/**
 * Filter analytics data by time range
 */
export function filterAnalyticsByTimeRange(analytics: any, timeRange: 'today' | '7days' | '30days' | 'all') {
  if (!analytics || timeRange === 'all') return analytics;

  const filteredData = { ...analytics };

  const timeRangeConfig = {
    today: {
      users: analytics.active_today || [],
      runsKey: 'runs_today' as const
    },
    '7days': {
      users: analytics.active_7days || [],
      runsKey: 'recent_runs' as const
    },
    '30days': {
      users: analytics.active_30days || [],
      runsKey: 'recent_runs' as const
    }
  };

  const config = timeRangeConfig[timeRange];
  if (!config) return analytics;

  const { users, runsKey } = config;

  // Transform data
  filteredData.top_users = mapToTopUsers(users, runsKey);
  filteredData.total_stats = calculateStats(users, runsKey);
  filteredData.status_breakdown = calculateStatusBreakdown(users);
  
  // top_blueprints is already filtered by time_range on the backend, so keep it as is
  // The backend returns time-filtered blueprints based on the time_range parameter

  return filteredData;
}

/**
 * Truncate user ID for display
 */
export function truncateUserId(userId: string, maxLength: number = 12): string {
  return userId.length > maxLength ? userId.substring(0, maxLength) + '...' : userId;
}

