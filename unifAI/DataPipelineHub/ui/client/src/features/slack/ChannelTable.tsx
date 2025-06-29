import { useMemo } from "react";
import { DataTable, DataTableColumn } from "@/components/ui/dataTable";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FaSync, FaCog, FaPlus, FaTrash } from "react-icons/fa";
import { HiOutlineLockClosed } from "react-icons/hi";
import { useLocation } from "wouter";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { EmbedChannel } from "./SlackIntegration";
import { Badge } from "@/components/ui/badge";

export function isChannelNew(createdAt: Date): boolean {
  const now = new Date()
  const dayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000)
  return createdAt > dayAgo
}

function StatusBadge({ 
  status, 
  isActivelyEmbedding = false 
}: { 
  status: EmbedChannel["status"];
  isActivelyEmbedding?: boolean;
}) {
  const { bgColor, textColor, label, isActive } = useMemo(() => {
    // Override status if actively embedding
    if (isActivelyEmbedding) {
      return {
        bgColor: "bg-blue-500/15",
        textColor: "text-blue-400",
        label: "Embedding...",
        isActive: true,
      };
    }

    switch (status) {
      case "ACTIVE":
        return {
          bgColor: "bg-emerald-500/15",
          textColor: "text-emerald-400",
          label: "In Progress",
          isActive: true,
        };
      case "PAUSED":
        return {
          bgColor: "bg-amber-500/15",
          textColor: "text-amber-400",
          label: "Paused",
          isActive: false,
        };
      case "DONE":
        return {
          bgColor: "bg-green-500/15",
          textColor: "text-green-400",
          label: "Done",
          isActive: false,
        };
      case "FAILED":
        return {
          bgColor: "bg-red-500/15",
          textColor: "text-red-400",
          label: "Failed",
          isActive: false,
        };
      case "ARCHIVED":
        return {
          bgColor: "bg-slate-600/10",
          textColor: "text-slate-400",
          label: "Archived",
          isActive: false,
        };
      default:
        return {
          bgColor: "bg-slate-600/10",
          textColor: "text-slate-400",
          label: status,
          isActive: false,
        };
    }
  }, [status, isActivelyEmbedding]);

  return (
    <span
      className={cn(
        "inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border",
        bgColor,
        textColor,
        isActive && "animate-pulse-glow border-emerald-400/30",
        !isActive && "border-current/20",
      )}
    >
      <span
        className={cn(
          "w-2 h-2 rounded-full mr-2",
          isActive ? "bg-emerald-400 animate-pulse" : "bg-current",
        )}
      ></span>
      {label}
    </span>
  );
}

export function getColumns(
  onSettingsClick: (ch: EmbedChannel) => void,
  onDeleteClick: (ch: EmbedChannel) => void,
  deletingChannelId?: string,
  activeEmbeddingIds: string[] = [],
): DataTableColumn<EmbedChannel>[] {
  return [
    {
      accessorKey: "name",
      header: "Channel",
      cell: ({ row }) => {
        const channel = row.original
        const isNew = channel.created && isChannelNew(new Date(channel.created))
        
        return (
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
            {channel.is_private ? (
                <HiOutlineLockClosed className="mr-2 h-4 w-4" />
              ) : (
                <span className="mr-2">#</span>
              )}
              <span className="font-medium text-foreground">
                {channel.name}
              </span>
              {isNew && (
                <Badge className="bg-green-500/20 text-green-400 animate-pulse border-green-400/30">
                  NEW
                </Badge>
              )}
            </div>
          </div>
        )
      }
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: (info) => {
        const channel = info.row.original;
        const isActivelyEmbedding = activeEmbeddingIds.includes(channel.channel_id);
        return (
          <StatusBadge 
            status={info.getValue<EmbedChannel["status"]>()} 
            isActivelyEmbedding={isActivelyEmbedding}
          />
        );
      },
      filterFn: (row, columnId, filterValue) => {
        const status = row.getValue(columnId) as EmbedChannel["status"];
        let displayLabel: string;
        
        switch (status) {
          case "ACTIVE":
            displayLabel = "In Progress";
            break;
          case "PAUSED":
            displayLabel = "Paused";
            break;
          case "DONE":
            displayLabel = "Done";
            break;
          case "FAILED":
            displayLabel = "Failed";
            break;
          case "ARCHIVED":
            displayLabel = "Archived";
            break;
          default:
            displayLabel = status;
        }
        
        return displayLabel === filterValue;
      },
      meta: {
        align: "center",
        filterType: "select",
        filterOptions: ["In Progress", "Paused", "Done", "Failed", "Archived"],
      },
    },
    {
      accessorKey: "messages",
      header: "Messages",
      cell: (info) => (
        <span className="text-muted-foreground">{info.getValue<string>()}</span>
      ),
      meta: { align: "left", filterType: "text" },
      filterFn: "includesString",
    },
    {
      accessorKey: "lastSync",
      header: "Last Sync",
      cell: (info) => (
        <span className="text-muted-foreground">{info.getValue<string>()}</span>
      ),
      meta: { align: "left", filterType: "text" },
      filterFn: "includesString",
    },
    {
      accessorKey: "created",
      header: "Created At",
      cell: (info) => (
        <span className="text-muted-foreground">{info.getValue<string>()}</span>
      ),
      sortingFn: (rowA, rowB, columnId) => {
        const dateA = new Date(rowA.getValue(columnId) as string);
        const dateB = new Date(rowB.getValue(columnId) as string);
        
        // Handle invalid dates
        if (isNaN(dateA.getTime()) && isNaN(dateB.getTime())) return 0;
        if (isNaN(dateA.getTime())) return 1;
        if (isNaN(dateB.getTime())) return -1;
        
        return dateA.getTime() - dateB.getTime();
      },
      meta: { align: "left", filterType: "text" },
      filterFn: "includesString",
    },
    {
      accessorKey: "is_private",
      header: "Privacy",
      cell: (info) => {
        const isPrivate = info.getValue<boolean>();
        const privacyText = isPrivate ? "Private" : "Public";
        return (
          <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
            isPrivate 
              ? "bg-amber-500/15 text-amber-400 border border-amber-400/20" 
              : "bg-blue-500/15 text-blue-400 border border-blue-400/20"
          }`}>
            {isPrivate ? (
              <>
                <HiOutlineLockClosed className="mr-1 h-3 w-3" />
                Private
              </>
            ) : (
              <>
                <span className="mr-1">#</span>
                Public
              </>
            )}
          </span>
        );
      },
      filterFn: (row, columnId, filterValue) => {
        const isPrivate = row.getValue(columnId) as boolean;
        const rowValue = isPrivate ? "Private" : "Public";
        return rowValue === filterValue;
      },
      meta: {
        align: "center",
        filterType: "select",
        filterOptions: [
          "Private",
          "Public"
        ],
      },
    },
    {
      accessorKey: "frequency",
      header: "Frequency",
      cell: (info) => (
        <span className="text-muted-foreground">{info.getValue<string>()}</span>
      ),
      meta: { align: "center", filterType: "text" },
      filterFn: "includesString",
    },
    {
      id: "actions",
      header: "Actions",
      enableSorting: false,
      cell: (info) => {
        const ch = info.row.original;
        const isDeleting = deletingChannelId === ch.channel_id;
        return (
          <div className="flex justify-end space-x-2">
            <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
              <Button
                variant="ghost"
                size="sm"
                className="p-2 text-muted-foreground hover:text-primary hover:bg-primary/10 rounded-lg transition-all duration-200"
                onClick={() => {
                  /* optional per-row refresh */
                }}
              >
                <FaSync className="h-4 w-4" />
              </Button>
            </motion.div>
            <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
              <Button
                variant="ghost"
                size="sm"
                className="p-2 text-muted-foreground hover:text-primary hover:bg-primary/10 rounded-lg transition-all duration-200"
                onClick={() => onSettingsClick(ch)}
              >
                <FaCog className="h-4 w-4" />
              </Button>
            </motion.div>
            <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
              <Button
                variant="ghost"
                size="sm"
                disabled={isDeleting}
                className={`p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg transition-all duration-200 ${
                  isDeleting ? "opacity-50 cursor-not-allowed" : ""
                }`}
                onClick={() => !isDeleting && onDeleteClick(ch)}
              >
                {isDeleting ? (
                  <FaSync className="h-4 w-4 animate-spin" />
                ) : (
                  <FaTrash className="h-4 w-4" />
                )}
              </Button>
            </motion.div>
          </div>
        );
      },
      meta: { align: "right" },
    },
  ];
}

interface PaginatedChannelTableProps {
  allChannels: EmbedChannel[];
  onSettingsClick: (channel: EmbedChannel) => void;
  onDeleteClick: (channel: EmbedChannel) => void;
  onRefresh: () => void;
  pageSize?: number;
  isLoading?: boolean;
  deletingChannelId?: string;
  activeEmbeddingIds?: string[];
}

export function PaginatedChannelTable({
  allChannels,
  onSettingsClick,
  onDeleteClick,
  onRefresh,
  pageSize = 6,
  isLoading = false,
  deletingChannelId,
  activeEmbeddingIds = [],
}: PaginatedChannelTableProps) {
  const [, navigate] = useLocation();

  if (isLoading) {
    return (
      <Card className="gradient-border shadow-2xl overflow-hidden">
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="h-6 w-48 rounded bg-gradient-to-r from-slate-600/20 via-slate-500/20 to-slate-600/20 bg-[length:200%_100%] animate-skeleton"></div>
            <div className="flex space-x-3">
              <div className="h-10 w-32 rounded-lg bg-gradient-to-r from-slate-600/20 via-slate-500/20 to-slate-600/20 bg-[length:200%_100%] animate-skeleton"></div>
              <div className="h-10 w-40 rounded-lg bg-gradient-to-r from-slate-600/20 via-slate-500/20 to-slate-600/20 bg-[length:200%_100%] animate-skeleton"></div>
            </div>
          </div>
          <div className="space-y-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="h-12 w-full rounded-lg bg-gradient-to-r from-slate-600/20 via-slate-500/20 to-slate-600/20 bg-[length:200%_100%] animate-skeleton"
              ></div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.1 }}
      className="w-full"
    >
      <Card className="gradient-border shadow-2xl overflow-hidden">
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-foreground">
              Channel Status Dashboard
            </h3>
            <div className="flex items-center space-x-3">
              <motion.div
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Button
                  onClick={() => navigate("/slack/add-source")}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 hover:-translate-y-0.5 hover:scale-105 hover:shadow-lg transition-all duration-200"
                >
                  <FaPlus className="mr-2" /> Add Channel
                </Button>
              </motion.div>
              <motion.div
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Button
                  variant="outline"
                  onClick={onRefresh}
                  className="px-4 py-2 border border-border text-foreground rounded-lg font-medium hover:bg-muted hover:-translate-y-0.5 hover:scale-105 hover:shadow-lg transition-all duration-200"
                >
                  <FaSync className="mr-2" /> Refresh Status
                </Button>
              </motion.div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <DataTable
              columns={getColumns(onSettingsClick, onDeleteClick, deletingChannelId, activeEmbeddingIds)}
              data={allChannels}
              enableSorting={true}
              enableColumnFilters={true}
              enablePagination={true}
              initialState={{
                pagination: { pageIndex: 0, pageSize },
                sorting: [],
              }}
            />
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
