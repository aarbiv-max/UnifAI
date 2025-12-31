import { CheckCircle2, Circle, Clock, AlertCircle } from 'lucide-react';

// Status colors and icons
export const getStatusConfig = (status: string) => {
  switch (status) {
    case 'done':
      return {
        icon: CheckCircle2,
        color: 'text-green-400',
        bgColor: 'bg-green-400/10',
        borderColor: 'border-green-400/30'
      };
    case 'in_progress':
      return {
        icon: Clock,
        color: 'text-blue-400',
        bgColor: 'bg-blue-400/10',
        borderColor: 'border-blue-400/30'
      };
    case 'failed':
      return {
        icon: AlertCircle,
        color: 'text-red-400',
        bgColor: 'bg-red-400/10',
        borderColor: 'border-red-400/30'
      };
    default: // pending
      return {
        icon: Circle,
        color: 'text-gray-400',
        bgColor: 'bg-gray-400/10',
        borderColor: 'border-gray-400/30'
      };
  }
};

/**
 * Map workflow execution status to work plan status
 */
function mapWorkflowStatusToWorkPlanStatus(status: string): string {
  const statusMap: Record<string, string> = {
    COMPLETED: 'done',
    RUNNING: 'in_progress',
    FAILED: 'failed',
    PENDING: 'pending',
    CANCELLED: 'pending', // Treat cancelled as pending (gray)
  };
  return statusMap[status] || 'pending';
}

/**
 * Get hex color for work plan status (for charts)
 */
function getWorkPlanStatusHexColor(workPlanStatus: string): string {
  const colorMap: Record<string, string> = {
    done: '#10B981',        // green-400
    in_progress: '#60A5FA',  // blue-400
    failed: '#F87171',      // red-400
    pending: '#9CA3AF',     // gray-400
  };
  return colorMap[workPlanStatus] || '#9CA3AF';
}

/**
 * Get hex color for workflow execution status
 * Uses the same color scheme as work plan statuses
 */
export function getWorkflowStatusColor(status: string): string {
  const workPlanStatus = mapWorkflowStatusToWorkPlanStatus(status);
  return getWorkPlanStatusHexColor(workPlanStatus);
}

/**
 * Get status color mapping for workflow execution statuses
 * Uses the same color scheme as WorkPlanDisplayHelpers
 */
export function getWorkflowStatusColors(): Record<string, string> {
  return {
    COMPLETED: getWorkflowStatusColor('COMPLETED'),
    FAILED: getWorkflowStatusColor('FAILED'),
    RUNNING: getWorkflowStatusColor('RUNNING'),
    PENDING: getWorkflowStatusColor('PENDING'),
    CANCELLED: getWorkflowStatusColor('CANCELLED'),
  };
}

// Format timestamp for display
export const formatTimestamp = (timestamp: string) => {
  return new Date(timestamp).toLocaleTimeString([], { 
    hour: '2-digit', 
    minute: '2-digit',
    second: '2-digit'
  });
};
