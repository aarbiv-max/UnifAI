import { FaEye, FaSync, FaTrash, FaLock, FaGlobe } from "react-icons/fa";
import { DataCard } from "@/components/shared/DataCard";
import { fileByColors, getFileIcon, statusByColors, statusByLabel } from "@/documents/helpers";
import { InlineLoader } from "@/components/shared/InlineLoader";
import { Document } from "@/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { DocumentData } from "./DocumentData";
import { PIPELINE_STATUS } from "@/constants/pipelineStatus";

interface DocumentGridProps {
  paginatedDocuments: Document[];
  activeDoc: Document | null;
  setActiveDoc: (doc: Document | null) => void;
  deleteLoading: boolean;
  onDeleteConfirmed: (id: string) => void;
  retrying: boolean;
  handleRetry: (id: string) => void;
  footer?: React.ReactNode;
}

const getSubtitle = (doc: Document) => {
  if (doc.status === PIPELINE_STATUS.ACTIVE) return <InlineLoader />;
  if (doc.status === PIPELINE_STATUS.PENDING || doc.status === PIPELINE_STATUS.FAILED) return "-";
  return `${doc.page_count} pages | ${doc.file_type} | ${doc.file_size}`;
};

const getFooterText = (doc: Document) => {
  if (doc.status === PIPELINE_STATUS.ACTIVE) return <InlineLoader />;
  if (doc.status === PIPELINE_STATUS.PENDING || doc.status === PIPELINE_STATUS.FAILED) return "-";
  return `${doc.chunks} chunks`;
};

const getStatusBadge = (doc: Document) => ({
  label: statusByLabel[doc.status] || "Unknown",
  className: statusByColors[doc.status],
});

const getPrivacyIcon = (doc: Document) => {
  return doc.scope === "public" ? (
    <FaGlobe className="h-3 w-3 text-blue-400" title="Public Document" />
  ) : (
    <FaLock className="h-3 w-3 text-gray-400" title="Private Document" />
  );
};

// const getExtraTopRight = (
//   doc: Document,
//   handleRetry: (id: string) => void,
//   retrying: boolean
// ) =>
//   doc.status === PIPELINE_STATUS.FAILED ? (
//     <Button
//       variant="ghost"
//       size="icon"
//       className="h-5 w-5 p-0"
//       onClick={(e) => {
//         e.stopPropagation();
//         handleRetry(doc.pipeline_id);
//       }}
//       disabled={retrying}
//     >
//       <FaSync className={`animate-spin ${retrying ? "" : "hidden"}`} />
//       {!retrying && <FaSync />}
//     </Button>
//   ) : null;

const getActions = (
  doc: Document,
  activeDoc: Document | null,
  setActiveDoc: (doc: Document | null) => void,
  deleteLoading: boolean,
  onDeleteConfirmed: (id: string) => void
) => [
  {
    icon: <FaEye />,
    onClick: () => setActiveDoc(doc === activeDoc ? null : doc),
  },
  {
    icon: <FaTrash className="h-3 w-3" />,
    onClick: () => {},
    confirm: {
      title: "Delete Document",
      message: `Are you sure you want to delete "${doc.name}"?`,
      onConfirm: () => onDeleteConfirmed(doc.pipeline_id),
      loading: deleteLoading,
      confirmLabel: "Yes, Delete",
    },
  },
];

export const DocumentGrid = ({paginatedDocuments, activeDoc, setActiveDoc, deleteLoading, onDeleteConfirmed, retrying, handleRetry, footer}: DocumentGridProps) => {
  return (
    <>
      <Card className="bg-background-card shadow-card border-gray-800">
        <CardContent className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {paginatedDocuments.map((doc) => (
              <DataCard
                key={doc.pipeline_id}
                iconRenderer={() => getFileIcon(doc.file_type)}
                iconBgClass={fileByColors[doc.file_type]}
                title={doc.name}
                subtitle={getSubtitle(doc)}
                metadata={
                  <div className="flex items-center justify-between">
                    <span>{`Uploaded ${new Date(doc.created_at).toLocaleString("en-GB")} by ${doc.upload_by}`}</span>
                    {getPrivacyIcon(doc)}
                  </div>
                }
                footer={getFooterText(doc)}
                selected={doc === activeDoc}
                onClick={() => setActiveDoc(doc === activeDoc ? null : doc)}
                statusBadge={getStatusBadge(doc)}
                // extraTopRight={getExtraTopRight(doc, handleRetry, retrying)}
                actions={getActions(doc, activeDoc, setActiveDoc, deleteLoading, onDeleteConfirmed)}
              />
            ))}
          </div>

          {footer && (
            <div className="mt-6 flex justify-between items-center">
              {footer}
            </div>
          )}
        </CardContent>
      </Card>

      {activeDoc && (
        <div className="mt-6">
          <DocumentData doc={activeDoc} />
        </div>
      )}
    </>
  );
};
