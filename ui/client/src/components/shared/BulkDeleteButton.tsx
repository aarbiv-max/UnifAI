import { Button } from "@/components/ui/button";
import { Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface BulkDeleteButtonProps {
  selectedCount: number;
  onClick: () => void;
  disabled?: boolean;
  itemName?: string;
  className?: string;
  compact?: boolean;
}

export function BulkDeleteButton({
  selectedCount,
  onClick,
  disabled = false,
  itemName = "Selected",
  className = "",
  compact = false,
}: BulkDeleteButtonProps) {
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      onClick={onClick}
      disabled={disabled || selectedCount === 0}
      className={cn(
        "shrink-0 rounded-lg font-medium shadow-sm",
        // Dark red surface + light copy: stays on-theme, higher contrast than faint destructive tint
        "border-red-900/60 bg-red-950/55 text-red-100",
        "hover:border-red-800/80 hover:bg-red-950/80 hover:text-red-50",
        "focus-visible:ring-2 focus-visible:ring-red-500/40 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        compact ? "h-8 gap-1.5 px-2.5 text-xs" : "h-9 gap-2 px-3.5 text-sm",
        "[&_svg]:text-red-200 [&_svg]:shrink-0",
        className,
      )}
    >
      <Trash2 className={cn("shrink-0", compact ? "h-3.5 w-3.5" : "h-4 w-4")} strokeWidth={2} />
      Delete {selectedCount} {itemName}
    </Button>
  );
}