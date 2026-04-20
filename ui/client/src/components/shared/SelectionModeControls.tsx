import { Button } from "@/components/ui/button";
import { BulkDeleteButton } from "./BulkDeleteButton";
import { ListChecks, Undo2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface SelectionModeControlsProps {
  /** Plural noun for the entry button, e.g. "chats", "workflows", "documents". */
  entityPluralLabel: string;
  isSelectionMode: boolean;
  onEnterSelectionMode: () => void;
  onExitSelectionMode: () => void;
  selectedCount: number;
  /** When false, only enter/exit selection is shown (e.g. element types in the catalog sidebar). */
  showBulkDelete?: boolean;
  onBulkDeleteClick?: () => void;
  bulkDeleteDisabled?: boolean;
  itemNameForDelete?: string;
  /** Select all / clear selection for the current list. Pass with onSelectAll + onClearSelection. */
  totalSelectable?: number;
  allSelected?: boolean;
  onSelectAll?: () => void;
  onClearSelection?: () => void;
  /** Tighter controls for narrow sidebars. */
  compact?: boolean;
  className?: string;
}

export function SelectionModeControls({
  entityPluralLabel,
  isSelectionMode,
  onEnterSelectionMode,
  onExitSelectionMode,
  selectedCount,
  showBulkDelete = true,
  onBulkDeleteClick,
  bulkDeleteDisabled = false,
  itemNameForDelete = "item",
  totalSelectable,
  allSelected = false,
  onSelectAll,
  onClearSelection,
  compact = false,
  className,
}: SelectionModeControlsProps) {
  const sizeClass = compact ? "h-8 text-xs px-2.5 gap-1.5" : "h-9 gap-2 px-3.5 text-sm";

  if (!isSelectionMode) {
    return (
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={onEnterSelectionMode}
        className={cn(
          "shrink-0 border-border/60 bg-background/40 text-foreground/80 shadow-sm",
          "hover:bg-muted/60 hover:text-foreground hover:border-border",
          sizeClass,
          className,
        )}
      >
        <ListChecks className={compact ? "h-3.5 w-3.5" : "h-4 w-4"} strokeWidth={2} />
        Select {entityPluralLabel}
      </Button>
    );
  }

  const showSelectAllCluster =
    Boolean(onSelectAll) &&
    typeof totalSelectable === "number" &&
    totalSelectable > 0 &&
    typeof onClearSelection === "function";

  const ghostSize = compact ? "h-8 px-2 text-[11px]" : "h-9 px-2.5 text-xs";

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-x-1.5 gap-y-1 shrink-0 justify-end",
        className,
      )}
    >
      {showBulkDelete && selectedCount > 0 && onBulkDeleteClick && (
        <BulkDeleteButton
          selectedCount={selectedCount}
          onClick={onBulkDeleteClick}
          disabled={bulkDeleteDisabled}
          itemName={itemNameForDelete}
          compact={compact}
        />
      )}
      {selectedCount > 0 && !showBulkDelete && (
        <span className="text-xs text-muted-foreground tabular-nums px-1">
          {selectedCount} selected
        </span>
      )}
      {showSelectAllCluster && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => (allSelected ? onClearSelection!() : onSelectAll!())}
          className={cn(
            "shrink-0 font-normal text-muted-foreground",
            "hover:bg-muted/50 hover:text-foreground",
            ghostSize,
          )}
        >
          {allSelected ? "Clear selection" : "Select all"}
        </Button>
      )}
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={onExitSelectionMode}
        className={cn(
          "shrink-0 border-muted-foreground/25 bg-muted/20 font-medium text-muted-foreground",
          "hover:bg-muted/40 hover:text-foreground",
          sizeClass,
        )}
      >
        <Undo2 className={compact ? "h-3.5 w-3.5" : "h-4 w-4"} strokeWidth={2} />
        Deselect
      </Button>
    </div>
  );
}
