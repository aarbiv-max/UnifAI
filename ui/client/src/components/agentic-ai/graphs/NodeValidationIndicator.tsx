import React from 'react';
import { AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react';
import { ElementValidationResult } from '@/types/validation';
import SimpleTooltip from '@/components/shared/SimpleTooltip';

interface NodeValidationIndicatorProps {
  validationResult?: ElementValidationResult;
  isValidating?: boolean;
  displayValid?: boolean;
  onClick?: (e: React.MouseEvent) => void;
  className?: string;
}

/**
 * A compact validation indicator component for displaying on graph nodes.
 * Shows a green checkmark for valid nodes (if displayValid=true),
 * a yellow warning for invalid nodes,
 * and a spinner while validation is in progress.
 */
export const NodeValidationIndicator: React.FC<NodeValidationIndicatorProps> = ({
  validationResult,
  isValidating = false,
  displayValid = true,
  onClick,
  className = '',
}) => {
  // Show spinner while validating
  if (isValidating) {
    return (
      <div
        className={`flex items-center justify-center ${className}`}
        onClick={(e) => e.stopPropagation()}
      >
        <SimpleTooltip content={<p>Validating...</p>}>
          <div className="p-2 rounded-full bg-gray-700/50">
            <Loader2 className="h-6 w-6 text-gray-400 animate-spin" />
          </div>
        </SimpleTooltip>
      </div>
    );
  }

  // Don't show anything if validation hasn't run yet
  if (!validationResult) {
    return null;
  }

  const isValid = validationResult.is_valid;

  // If valid results shouldn't be displayed, hide them
  if (isValid && !displayValid) {
    return null;
  }

  // Count issues by severity
  const errorCount = validationResult.messages.filter(m => m.severity === 'error').length;
  const warningCount = validationResult.messages.filter(m => m.severity === 'warning').length;

  const tooltipContent = isValid
    ? 'Validation passed'
    : `${errorCount} error${errorCount !== 1 ? 's' : ''}${
        warningCount > 0
          ? `, ${warningCount} warning${warningCount !== 1 ? 's' : ''}`
          : ''
}`;

  return (
    <div
      className={`flex items-center justify-center cursor-pointer transition-transform hover:scale-110 ${className}`}
      onClick={(e) => {
        e.stopPropagation();
        if (!isValid) onClick?.(e);
      }}
    >
      <SimpleTooltip content={<p>{tooltipContent}</p>}>
        <div
          className={`p-2 rounded-full ${
            isValid
              ? 'bg-green-500/20 hover:bg-green-500/30'
              : 'bg-yellow-500/20 hover:bg-yellow-500/30'
          }`}
        >
          {isValid ? (
            <CheckCircle2 className="h-6 w-6 text-green-500" />
          ) : (
            <AlertTriangle className="h-6 w-6 text-yellow-500" />
          )}
        </div>
      </SimpleTooltip>
    </div>
  );
};

export default NodeValidationIndicator;
