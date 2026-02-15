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

