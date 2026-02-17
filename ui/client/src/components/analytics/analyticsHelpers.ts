/**
 * Analytics Helper Utilities
 * 
 * Shared functions for analytics data transformations and calculations.
 * Note: The backend now handles all time-range filtering, so client-side
 * recomputation is no longer needed.
 */

import type { TimeRange } from "@/types/systemStats";

/**
 * Truncate user ID for display
 */
export function truncateUserId(userId: string, maxLength: number = 12): string {
  return userId.length > maxLength ? userId.substring(0, maxLength) + '...' : userId;
}

/**
 * Shared Recharts tooltip styles for all analytics charts.
 * Keeps chart styling consistent across StatusBreakdown, TopUsers, and WorkflowExecution charts.
 */
export const CHART_TOOLTIP_CONTENT_STYLE = {
  backgroundColor: '#374151',
  border: '1px solid #6B7280',
  borderRadius: '0.375rem',
};

export const CHART_TOOLTIP_LABEL_STYLE = {
  color: '#F9FAFB',
};

/**
 * Return a human-readable suffix for the given time range.
 * Compose with a prefix like "Workflow Executions" or "Other Statistic" to build titles.
 */
export function getTimeRangeSuffix(range: TimeRange): string {
  switch (range) {
    case 'today':
      return 'Today (by Hour)';
    case '7days':
      return '(Last 7 Days)';
    case '30days':
      return '(Last 30 Days)';
    case 'all':
      return '(All Time by Month)';
    default:
      return 'Over Time';
  }
}

/**
 * Format a period string into a display-friendly label based on the active time range.
 *
 * - "today"  : "2024-01-15 14:00" → "2:00 PM"
 * - "all"    : "2024-01"          → "Jan 2024"
 * - default  : "2024-01-15"       → "Jan 15"
 */
export function formatPeriodLabel(period: string, range: string): string {
  if (!period) return '';

  try {
    if (range === 'today') {
      return formatHourlyPeriod(period);
    } else if (range === 'all') {
      return formatMonthlyPeriod(period);
    } else {
      return formatDailyPeriod(period);
    }
  } catch {
    return period;
  }
}

/** Parse a date-like string into a Date, handling common period formats. */
function parsePeriodDate(period: string, fallbackSuffix: string): Date | null {
  let date: Date | null = null;
  if (period.includes('T') || period.includes('Z')) {
    date = new Date(period);
  } else if (period.includes(' ')) {
    date = new Date(period + fallbackSuffix);
  } else {
    date = new Date(period + fallbackSuffix);
  }
  return date && !isNaN(date.getTime()) ? date : null;
}

/** "2024-01-15 14:00" → "2:00 PM" */
function formatHourlyPeriod(period: string): string {
  const date = parsePeriodDate(period, ':00Z');
  if (date) {
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
  }

  // Fallback: extract hour from "2024-01-15 14:00"
  const parts = period.split(' ');
  if (parts.length > 1) {
    const hourStr = parts[1].split(':')[0];
    const hour = parseInt(hourStr);
    if (!isNaN(hour)) {
      const ampm = hour >= 12 ? 'PM' : 'AM';
      const displayHour = hour % 12 || 12;
      return `${displayHour}:00 ${ampm}`;
    }
  }
  return period;
}

/** "2024-01" → "Jan 2024" */
function formatMonthlyPeriod(period: string): string {
  const parts = period.split('-');
  if (parts.length === 2) {
    const year = parts[0];
    const month = parseInt(parts[1], 10);
    if (!isNaN(month) && month >= 1 && month <= 12) {
      const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      return `${monthNames[month - 1]} ${year}`;
    }
  }
  return period;
}

/** "2024-01-15" → "Jan 15" */
function formatDailyPeriod(period: string): string {
  const date = parsePeriodDate(period, 'T00:00:00Z');
  if (date) {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }
  return period;
}

