// components/ui/dataTable.tsx
import * as React from "react";
import {
  ColumnDef,
  SortingFn,
  SortingState,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
  flexRender,
  filterFns, // ← register built‐in filters
} from "@tanstack/react-table";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "./table";
import { cn } from "@/lib/utils";
import {
  LiaSortSolid,
  LiaSortUpSolid,
  LiaSortDownSolid,
} from "react-icons/lia";

//
// ─── SORT HELPERS ───────────────────────────────────────────────────────
//

// 1) Numeric sort
const numericSort: SortingFn<any> = (rowA, rowB, columnId) => {
  const parseValue = (val: unknown) => {
    if (typeof val === "number") return val;
    const str = String(val);
    const cleaned = str.replace(/[^0-9.-]/g, "");
    const parsed = parseFloat(cleaned);
    return isNaN(parsed) ? NaN : parsed;
  };

  const a = parseValue(rowA.getValue(columnId));
  const b = parseValue(rowB.getValue(columnId));
  if (isNaN(a) && isNaN(b)) return 0;
  if (isNaN(a)) return 1;
  if (isNaN(b)) return -1;
  return a - b;
};

// 2) Alphanumeric sort
const alphanumericSort: SortingFn<any> = (rowA, rowB, columnId) => {
  const rawA = rowA.getValue(columnId);
  const rawB = rowB.getValue(columnId);
  if (rawA == null && rawB == null) return 0;
  if (rawA == null) return 1;
  if (rawB == null) return -1;
  const a = String(rawA);
  const b = String(rawB);
  return a.localeCompare(b, undefined, {
    numeric: true,
    sensitivity: "base",
  });
};

type DataTableColumnMeta = {
  align?: "left" | "center" | "right";
};
export type DataTableColumn<T> = ColumnDef<T, any> & {
  meta?: DataTableColumnMeta;
};

interface DataTableProps<T extends object> {
  columns: DataTableColumn<T>[];
  data: T[];
  enableSorting?: boolean;
  enableFiltering?: boolean;
  enablePagination?: boolean;
  initialState?: Partial<{
    sorting: SortingState;
    globalFilter: string;
    pagination: { pageIndex: number; pageSize: number };
  }>;
  onSortingChange?: (updater: SortingState) => void;
}

export function DataTable<T extends object>({
  columns,
  data,
  enableSorting = true,
  enableFiltering = false,
  enablePagination = true,
  initialState,
  onSortingChange,
}: DataTableProps<T>) {
  const [sorting, setSorting] = React.useState<SortingState>(
    initialState?.sorting ?? []
  );
  const [globalFilter, setGlobalFilter] = React.useState(
    initialState?.globalFilter ?? ""
  );
  const [pagination, setPagination] = React.useState({
    pageIndex: initialState?.pagination?.pageIndex ?? 0,
    pageSize: initialState?.pagination?.pageSize ?? 10,
  });

  // ─── Auto‐assign sortingFn based on data type ─────────────────────────
  const processedColumns = React.useMemo(() => {
    return columns.map((col) => {
      if (col.enableSorting === false) return col;
      if (col.sortingFn) return col;

      const accessorKey = (col as any).accessorKey;
      if (typeof accessorKey !== "string") {
        return { ...col, sortingFn: alphanumericSort };
      }

      const sampleRow = data.find(
        (row: T) => (row as Record<string, unknown>)[accessorKey] != null
      );
      const sampleValue = sampleRow
        ? (sampleRow as Record<string, unknown>)[accessorKey]
        : undefined;

      const isNumeric =
        sampleValue != null &&
        !isNaN(
          parseFloat(String(sampleValue).replace(/[^0-9.-]/g, ""))
        );

      return {
        ...col,
        sortingFn: isNumeric ? numericSort : alphanumericSort,
      };
    });
  }, [columns, data]);

  // ─── Initialize TanStack table with filtering, sorting, pagination ────
  const table = useReactTable({
    data,
    columns: processedColumns,
    state: {
      sorting: enableSorting ? sorting : [],
      globalFilter: enableFiltering ? globalFilter : undefined,
      pagination: enablePagination ? pagination : undefined,
    },
    enableSorting,
    enableGlobalFilter: enableFiltering,
    enableMultiSort: true,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: enableFiltering ? getFilteredRowModel() : undefined,
    getSortedRowModel: enableSorting ? getSortedRowModel() : undefined,
    getPaginationRowModel: enablePagination
      ? getPaginationRowModel()
      : undefined,
    filterFns, // ← register all built‐in filters here
    onSortingChange: (updater) => {
      setSorting(updater);
      if (onSortingChange) {
        const nextSorting =
          typeof updater === "function" ? updater(sorting) : updater;
        onSortingChange(nextSorting);
      }
    },
    onGlobalFilterChange: setGlobalFilter,
    onPaginationChange: setPagination,
    initialState: {
      sorting: initialState?.sorting ?? [],
      globalFilter: initialState?.globalFilter ?? "",
      pagination: initialState?.pagination ?? { pageIndex: 0, pageSize: 10 },
    },
  });

  return (
    <div className="w-full">
      {/* ─── Global Filter ─────────────────────────────────────────────── */}
      {enableFiltering && (
        <div className="mb-4 flex items-center space-x-2">
          <input
            type="text"
            value={table.getState().globalFilter ?? ""}
            onChange={(e) => table.setGlobalFilter(e.target.value)}
            placeholder="Search all columns..."
            className="border rounded px-2 py-1 text-sm"
          />
        </div>
      )}

      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <React.Fragment key={headerGroup.id}>
              <TableRow>
                {headerGroup.headers.map((header) => {
                  const canSort = enableSorting && header.column.getCanSort();
                  const isSorted = header.column.getIsSorted();
                  const align = (header.column.columnDef as any).meta?.align;

                  return (
                    <TableHead
                      key={header.id}
                      className={cn(
                        align === "center"
                          ? "text-center"
                          : align === "right"
                            ? "text-right"
                            : "text-left",
                        canSort && "cursor-pointer select-none"
                      )}
                      onClick={
                        canSort
                          ? () => header.column.toggleSorting(undefined, true)
                          : undefined
                      }
                    >
                      <div className="inline-flex items-center">
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                        {canSort && (
                          <span className="ml-1 flex-shrink-0">
                            {isSorted === "asc" ? (
                              <LiaSortUpSolid className="h-4 w-4 text-primary" />
                            ) : isSorted === "desc" ? (
                              <LiaSortDownSolid className="h-4 w-4 text-primary" />
                            ) : (
                              <LiaSortSolid className="h-4 w-4 text-gray-400" />
                            )}
                          </span>
                        )}
                      </div>
                    </TableHead>
                  );
                })}
              </TableRow>

              {/* ─── Per-Column Filter Row ─────────────────────────────── */}
              {enableFiltering && (
                <TableRow>
                  {headerGroup.headers.map((header) => {
                    const canFilter = header.column.getCanFilter();
                    const align = (header.column.columnDef as any).meta?.align;
                    return (
                      <TableCell
                        key={`${header.id}-filter`}
                        className={cn(
                          "pt-1",
                          align === "center"
                            ? "text-center"
                            : align === "right"
                              ? "text-right"
                              : "text-left"
                        )}
                      >
                        {canFilter ? (
                          <input
                            type="text"
                            value={(header.column.getFilterValue() ?? "") as string}
                            onChange={(e) =>
                              header.column.setFilterValue(e.target.value)
                            }
                            placeholder={`Filter...`}
                            className="w-full border rounded px-1 py-0.5 text-xs"
                          />
                        ) : null}
                      </TableCell>
                    );
                  })}
                </TableRow>
              )}
            </React.Fragment>
          ))}
        </TableHeader>

        <TableBody>
          {table.getRowModel().rows.length ? (
            table.getRowModel().rows.map((row) => (
              <TableRow key={row.id}>
                {row.getVisibleCells().map((cell) => {
                  const align = (cell.column.columnDef as any).meta?.align;
                  return (
                    <TableCell
                      key={cell.id}
                      className={cn(
                        align === "center"
                          ? "text-center"
                          : align === "right"
                            ? "text-right"
                            : undefined
                      )}
                    >
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={columns.length} className="text-center py-4">
                No data to display.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      {enablePagination && (
        <div className="flex items-center justify-between py-4">
          <span className="text-sm text-gray-500">
            Page{" "}
            <strong>
              {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
            </strong>
          </span>
          <div className="flex items-center space-x-2">
            <button
              className="px-2 py-1 border rounded disabled:opacity-50"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
            >
              Previous
            </button>
            <button
              className="px-2 py-1 border rounded disabled:opacity-50"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
