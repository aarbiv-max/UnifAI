/**
 * Analytics Helper Utilities
 * 
 * Shared functions for analytics data transformations and calculations.
 * Note: The backend now handles all time-range filtering, so client-side
 * recomputation is no longer needed.
 */

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

