import React, { useState } from "react";
import { FaEye, FaTrash, FaSync, FaLock, FaGlobe } from "react-icons/fa";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { InlineLoader } from "@/components/shared/InlineLoader";
import { Document } from "@/types";
import { getFileIcon, fileByColors, statusByLabel, statusByColors } from "./helpers";
import { DataTable, DataTableColumn } from "@/components/shared/DataTable";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { DocumentData } from "./DocumentData";
import { PIPELINE_STATUS } from "@/constants/pipelineStatus";

interface DocumentTableProps {
  documents: Document[];
  activeDoc?: Document | null;
  setActiveDoc?: (doc: Document | null) => void;
  deleteLoading?: boolean; // Optional: legacy
  onDeleteConfirmed?: (id: string) => void;
  retrying?: boolean;
  handleRetry?: (id: string) => void;
}

export const DocumentTable: React.FC<DocumentTableProps> = ({documents, activeDoc, setActiveDoc, deleteLoading, onDeleteConfirmed, retrying, handleRetry}) => {
  const [confirmDoc, setConfirmDoc] = useState<Document | null>(null);
  const [confirmLoading, setConfirmLoading] = useState(false);

  const columns: DataTableColumn<Document>[] = [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => {
        const doc = row.original;
        return (
          <div className="flex items-center space-x-2">
            <div className={`p-1.5 rounded ${fileByColors[doc.file_type]}`}>
              {getFileIcon(doc.file_type)}
            </div>
            <div className="truncate max-w-[200px]">{doc.name}</div>
          </div>
        );
      },
      meta: { align: "left", filterType: "text" },
    },
    {
      accessorKey: "created_at",
      header: "Uploaded At",
      cell: ({ row }) =>
        new Date(row.original.created_at).toLocaleString("en-GB"),
      meta: { align: "left" },
    },
    {
      accessorKey: "upload_by",
      header: "Uploaded By",
      cell: ({ row }) => row.original.upload_by,
      meta: { align: "left" },
    },
    {
      accessorKey: "privacy",
      header: "Privacy",
      cell: ({ row }) => {
        const doc = row.original;
        return (
          <div className="flex items-center justify-center">
            {doc.scope === "public" ? (
              <div className="flex items-center space-x-1">
                <FaGlobe className="h-3 w-3 text-blue-400" />
                <span className="text-xs text-blue-400">Public</span>
              </div>
            ) : (
              <div className="flex items-center space-x-1">
                <FaLock className="h-3 w-3 text-gray-400" />
                <span className="text-xs text-gray-400">Private</span>
              </div>
            )}
          </div>
        );
      },
      meta: { 
        align: "center", 
        filterType: "select",
        filterOptions: ["private", "public"],
      },
    },
    {
      accessorKey: "page_count",
      header: "Pages",
      cell: ({ row }) => {
        const doc = row.original;
        return doc.status === PIPELINE_STATUS.ACTIVE ? (
          <InlineLoader />
        ) : doc.status === PIPELINE_STATUS.PENDING ? (
          "-"
        ) : (
          doc.page_count
        );
      },
      meta: { align: "center" },
    },
    {
      accessorKey: "file_size",
      header: "Size (MB)",
      cell: ({ row }) => {
        const doc = row.original;
        if (doc.status === PIPELINE_STATUS.ACTIVE) return <InlineLoader />;
        if (doc.status === PIPELINE_STATUS.PENDING) return "-";
        const sizeMatch = doc.file_size?.match(/[\d.]+/);
        return sizeMatch ? sizeMatch[0] : "-";
      },
      meta: { align: "center" },
    },
    {
      accessorKey: "file_type",
      header: "File Type",
      cell: ({ row }) => row.original.file_type.toUpperCase(),
      meta: {
        align: "center",
        filterType: "select",
        filterOptions: ["PDF", "DOCX", "TXT", "XLSX", "OTHER"],
      },
    },
    {
      accessorKey: "chunks",
      header: "Chunks",
      cell: ({ row }) => {
        const doc = row.original;
        return doc.status === PIPELINE_STATUS.ACTIVE ? (
          <InlineLoader />
        ) : doc.status === PIPELINE_STATUS.PENDING ? (
          "-"
        ) : (
          `${doc.chunks}`
        );
      },
      meta: { align: "center" },
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => {
        const doc = row.original;
        return (
          <Badge className={`text-xs ${statusByColors[doc.status]}`}>
            {statusByLabel[doc.status] || "Unknown"}
          </Badge>
        );
      },
      meta: {
        align: "center",
        filterType: "select",
        filterOptions: Object.keys(statusByLabel),
      },
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => {
        const doc = row.original;
        const isActive = activeDoc?.pipeline_id === doc.pipeline_id;
        return (
          <div className="flex items-center space-x-2 justify-end">
            {/* {doc.status === PIPELINE_STATUS.FAILED && (
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 p-0"
                onClick={() => handleRetry?.(doc.pipeline_id)}
                disabled={retrying}
              >
                <FaSync />
              </Button>
            )} */}
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 p-0"
              onClick={() => setActiveDoc?.(isActive ? null : doc)}
            >
              <FaEye className={isActive ? "text-primary" : ""} />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 p-0"
              onClick={() => {
                setConfirmDoc(doc);
                setConfirmLoading(false);
              }}
              disabled={deleteLoading || confirmLoading}
            >
              <FaTrash className="h-3 w-3" />
            </Button>
          </div>
        );
      },
      meta: { align: "right" },
    },
  ];

  return (
    <div className="w-full">
      <DataTable
        columns={columns}
        data={documents}
        enableGlobalFilter={false}
        enableColumnFilters={true}
        enablePagination={true}
        expendedRow={activeDoc}
        renderExpandedRow={(doc) => <DocumentData doc={doc} />}
      />

      {confirmDoc && (
        <ConfirmDialog
          open={true}
          title="Delete Document"
          message={`Are you sure you want to delete "${confirmDoc.name}"?`}
          confirmLabel="Yes, Delete"
          loading={confirmLoading}
          onCancel={() => {
            if (!confirmLoading) setConfirmDoc(null);
          }}
          onConfirm={async () => {
            try {
              setConfirmLoading(true);
              await onDeleteConfirmed?.(confirmDoc.pipeline_id);
              setConfirmDoc(null);
            } catch (err) {
              console.error("Delete failed:", err);
            } finally {
              setConfirmLoading(false);
            }
          }}
        />
      )}
    </div>
  );
};
