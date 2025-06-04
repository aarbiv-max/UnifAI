// features/slack/ChannelTable.tsx
import { useMemo } from "react";
import { DataTable, DataTableColumn } from "@/components/ui/dataTable";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FaSync, FaCog, FaPlus } from "react-icons/fa";
import { useLocation } from "wouter";

export interface Channel {
  name: string;
  messages: string;
  lastSync: string;
  status: "Active" | "Paused" | "Archived";
  frequency: string;
}

function StatusBadge({ status }: { status: Channel["status"] }) {
  const { bgColor, textColor, label } = useMemo(() => {
    switch (status) {
      case "Active":
        return { bgColor: "bg-green-100", textColor: "text-green-800", label: "Active" };
      case "Paused":
        return { bgColor: "bg-yellow-100", textColor: "text-yellow-800", label: "Paused" };
      default:
        return { bgColor: "bg-gray-200", textColor: "text-gray-600", label: "Archived" };
    }
  }, [status]);

  return (
    <span className={`px-2 py-0.5 rounded-full ${bgColor} ${textColor} text-sm font-medium`}>
      {label}
    </span>
  );
}

//
// ─── Column Definitions (use `filterFn`, NOT `enableFiltering`) ─────────────────
//

function getColumns(onSettingsClick: (ch: Channel) => void): DataTableColumn<Channel>[] {
  return [
    {
      accessorKey: "name",
      header: "Channel",
      cell: (info) => <span className="font-medium">#{info.getValue<string>()}</span>,
      meta: { align: "left" },
      filterFn: "includesString",       // ← substring filter on `name`
    },
    {
      accessorKey: "messages",
      header: "Messages",
      meta: { align: "left" },
      filterFn: "includesString",       // ← substring filter on `messages`
    },
    {
      accessorKey: "lastSync",
      header: "Last Sync",
      meta: { align: "left" },
      filterFn: "includesString",       // ← substring filter on `lastSync`
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: (info) => <StatusBadge status={info.getValue<Channel["status"]>()} />,
      meta: { align: "center" },
      filterFn: "equalsString",         // ← exact, case-insensitive match on `status`
    },
    {
      accessorKey: "frequency",
      header: "Frequency",
      meta: { align: "center" },
      filterFn: "includesString",       // ← substring filter on `frequency`
    },
    {
      id: "actions",
      header: "Actions",
      enableSorting: false,
      cell: (info) => {
        const ch = info.row.original;
        return (
          <div className="flex justify-end space-x-2">
            <Button variant="ghost" size="sm" onClick={() => {/* optional per-row refresh */}}>
              <FaSync className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={() => onSettingsClick(ch)}>
              <FaCog className="h-4 w-4" />
            </Button>
          </div>
        );
      },
      meta: { align: "right" },
      // No `filterFn` here, so this column will not show a filter input
    },
  ];
}

//
// ─── Table Component ──────────────────────────────────────────────────────
//

interface ChannelTableProps {
  channels: Channel[];
  onSettingsClick: (channel: Channel) => void;
  onRefresh: () => void;
  currentPage: number;
  pageSize: number;
  totalCount: number;
  onPageChange: (newPage: number) => void;
}

export function ChannelTable({
  channels,
  onSettingsClick,
  onRefresh,
  currentPage,
  pageSize,
  totalCount,
  onPageChange,
}: ChannelTableProps) {
  const [, navigate] = useLocation();

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const canPrev = currentPage > 1;
  const canNext = currentPage < totalPages;
  const startIndex = totalCount === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const endIndex = Math.min(currentPage * pageSize, totalCount);

  return (
    <Card className="bg-background-card shadow-card border-gray-800">
      <CardContent className="p-6">
        {/* HEADER */}
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-heading font-semibold">Channel Status Dashboard</h3>
          <div className="flex items-center space-x-2">
            <Button onClick={() => navigate("/slack/add-source")}>
              <FaPlus className="mr-2" /> Add Source
            </Button>
            <Button variant="outline" onClick={onRefresh}>
              <FaSync className="mr-2" /> Refresh Status
            </Button>
          </div>
        </div>

        {/* DATA TABLE */}
        <div className="overflow-x-auto">
          <DataTable<Channel>
            columns={getColumns(onSettingsClick)}
            data={channels}
            enableSorting={true}
            enableFiltering={true}      
            enablePagination={true}
            initialState={{
              pagination: { pageIndex: currentPage - 1, pageSize },
            }}
          />
        </div>

        {/* PAGINATION CONTROLS */}
        <div className="mt-6 flex items-center justify-between">
          <span className="text-sm text-gray-400">
            {totalCount === 0 ? (
              <>Showing <strong>0</strong> of <strong>0</strong></>
            ) : (
              <>
                Showing <strong>{startIndex}–{endIndex}</strong> of <strong>{totalCount}</strong>
              </>
            )}
          </span>
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              disabled={!canPrev}
              onClick={() => canPrev && onPageChange(currentPage - 1)}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!canNext}
              onClick={() => canNext && onPageChange(currentPage + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

//
// ─── 4. FULL-PAGE / PAGINATED WRAPPER ────────────────────────────────────────────
//

interface PaginatedChannelTableProps {
  allChannels: Channel[];
  onSettingsClick: (channel: Channel) => void;
  onRefresh: () => void;
  /** Optional override of items per page; default = 6. */
  pageSize?: number;
}

export function PaginatedChannelTable({
  allChannels,
  onSettingsClick,
  onRefresh,
  pageSize = 6,
}: PaginatedChannelTableProps) {
  const [, navigate] = useLocation();

  // For a fully client-side version, you could just render allChannels here
  // with pagination inside DataTable instead of slicing externally.

  return (
    <Card className="bg-background-card shadow-card border-gray-800">
      <CardContent className="p-6">
        {/* HEADER / TOOLBAR */}
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-heading font-semibold">Channel Status Dashboard</h3>
          <div className="flex items-center space-x-2">
            <Button onClick={() => navigate("/slack/add-source")}>
              <FaPlus className="mr-2" /> Add Source
            </Button>
            <Button variant="outline" onClick={onRefresh}>
              <FaSync className="mr-2" /> Refresh Status
            </Button>
          </div>
        </div>

        {/* FULL DATA TABLE (pagination inside DataTable) */}
        <div className="overflow-x-auto">
          <DataTable<Channel>
            columns={getColumns(onSettingsClick)}
            data={allChannels}
            enableSorting={true}
            enableFiltering={true}       
            enablePagination={true}
            initialState={{
              pagination: { pageIndex: 0, pageSize },
              sorting: [],
            }}
          />
        </div>
      </CardContent>
    </Card>
  );
}
