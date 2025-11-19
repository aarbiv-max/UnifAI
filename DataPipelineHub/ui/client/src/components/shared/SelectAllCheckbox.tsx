import { Checkbox } from "@/components/ui/checkbox";
import { RowSelectionState, Table as TanStackTable } from "@tanstack/react-table";

interface SelectAllCheckboxProps<T> {
  table: TanStackTable<T>;
  rowSelection: RowSelectionState;
  onRowSelectionChange: (selection: RowSelectionState) => void;
  getRowId: (row: T) => string;
  align?: "left" | "center" | "right";
}

export function SelectAllCheckbox<T>({
  table,
  rowSelection,
  onRowSelectionChange,
  getRowId,
  align = "right",
}: SelectAllCheckboxProps<T>) {
  const filteredRows = table.getFilteredRowModel().rows;
  const isAllFilteredSelected = filteredRows.length > 0 && filteredRows.every(row => {
    const rowId = getRowId(row.original);
    return rowSelection[rowId];
  });
  
  const alignmentClass = align === "center" ? "justify-center" : align === "left" ? "justify-start" : "justify-end";
  
  return (
    <div className={`flex items-center ${alignmentClass}`}>
      <div 
        className="flex items-center"
        onClick={(e) => e.stopPropagation()}
      >
        <Checkbox
          checked={isAllFilteredSelected}
          onCheckedChange={(checked) => {
            const newSelection = { ...rowSelection };
            if (checked) {
              filteredRows.forEach(row => {
                const rowId = getRowId(row.original);
                newSelection[rowId] = true;
              });
            } else {
              filteredRows.forEach(row => {
                const rowId = getRowId(row.original);
                delete newSelection[rowId];
              });
            }
            onRowSelectionChange(newSelection);
          }}
          aria-label="Select all filtered rows"
        />
      </div>
    </div>
  );
}

