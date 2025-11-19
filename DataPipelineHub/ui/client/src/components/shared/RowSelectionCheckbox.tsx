import { Checkbox } from "@/components/ui/checkbox";
import { RowSelectionState } from "@tanstack/react-table";

interface RowSelectionCheckboxProps {
  rowId: string;
  rowSelection: RowSelectionState;
  onRowSelectionChange: (selection: RowSelectionState) => void;
  ariaLabel?: string;
}

export function RowSelectionCheckbox({
  rowId,
  rowSelection,
  onRowSelectionChange,
  ariaLabel,
}: RowSelectionCheckboxProps) {
  const isSelected = rowSelection[rowId] === true;
  
  return (
    <div 
      className="flex items-center"
      onClick={(e) => e.stopPropagation()}
    >
      <Checkbox
        checked={isSelected}
        onCheckedChange={(checked) => {
          const newSelection = { ...rowSelection };
          if (checked) {
            newSelection[rowId] = true;
          } else {
            delete newSelection[rowId];
          }
          onRowSelectionChange(newSelection);
        }}
        aria-label={ariaLabel || `Select row ${rowId}`}
      />
    </div>
  );
}

