import React from 'react';
import { Sparkles } from 'lucide-react';

export interface AIGeneratedBadgeProps {
  /** Custom class name for the container */
  className?: string;
  /** Badge size variant */
  size?: 'sm' | 'md';
}

export const AIGeneratedBadge: React.FC<AIGeneratedBadgeProps> = ({
  className = '',
  size = 'md',
}) => {
  const iconSize = size === 'sm' ? 'h-3 w-3' : 'h-3.5 w-3.5';
  const textSize = size === 'sm' ? 'text-[10px]' : 'text-xs';
  const padding = size === 'sm' ? 'px-1.5 py-0.5' : 'px-2 py-1';

  return (
    <div
      className={`inline-flex items-center gap-1.5 ${padding} rounded-md border ${className}`}
      style={{ borderColor: 'hsl(var(--primary) / 0.3)' }}
      role="status"
      aria-label="AI-generated content"
    >
      <Sparkles
        className={iconSize}
        style={{ color: 'hsl(var(--primary) / 0.85)' }}
        aria-hidden="true"
      />
      <span className={`${textSize} font-medium text-gray-300/90 tracking-wide`}>
        AI Generated
      </span>
    </div>
  );
};

export default AIGeneratedBadge;

