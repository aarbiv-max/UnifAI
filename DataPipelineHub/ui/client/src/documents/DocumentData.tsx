import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FaEye, FaSync, FaTrash, FaLock, FaGlobe } from "react-icons/fa";
import { getFileIcon } from "./helpers";
import { Document } from "@/types";

interface LibraryTabProps {
  doc: Document;
}

// the commented out fields are placeholders for future enhancements
export const DocumentData: React.FC<LibraryTabProps> = ({ doc }) => {
  const metadata = [
    { label: "Title", value: doc.name },
    // { label: "Author", value: "Product Management Team" },
    { label: "Created", value: new Date(doc.created_at).toLocaleDateString() },
    { label: "Modified", value: doc.last_updated ? new Date(doc.last_updated).toLocaleDateString() : "—" },
    { label: "File Size", value: doc.file_size },
    { label: "Pages", value: doc.page_count },
    { label: "Uploaded", value: new Date(doc.created_at).toLocaleDateString() },
    { label: "Processed", value: doc.last_updated ? new Date(doc.last_updated).toLocaleDateString() : "—" },
    { 
      label: "Privacy", 
      value: (
        <div className="flex items-center space-x-1">
          {doc.scope === "public" ? (
            <>
              <FaGlobe className="h-3 w-3 text-blue-400" />
              <span className="text-blue-400">Public</span>
            </>
          ) : (
            <>
              <FaLock className="h-3 w-3 text-gray-400" />
              <span className="text-gray-400">Private</span>
            </>
          )}
        </div>
      )
    },
  ];

  const statistics = [
    // { label: "Text Quality", value: "Excellent", progress: 95, color: "bg-success" },
    // { label: "Structure Preservation", value: "Good", progress: 85, color: "bg-primary" },
    { label: "Total Chunks", value: doc.chunks },
    // { label: "Total Tokens", value: doc.stats?.total_tokens || "—" },
    // { label: "Avg. Chunk Size", value: doc.stats?.avg_chunk_size || "—" },
    // { label: "Images Extracted", value: doc.stats?.images_extracted || "—" },
    // { label: "Tables Extracted", value: doc.stats?.tables_extracted || "—" },
    { label: "Embeddings Created", value: doc.stats?.embeddings_created ?? "—" },
    { label: "API Calls", value: doc.stats?.api_calls ?? "—" },
    { label: "Processing Time (s)", value: doc.stats?.processing_time?.toFixed(2) ?? "—" },
  ];

  return (
    <div className="grid grid-cols-1 gap-6">
      <Card className="bg-background-card shadow-card border-gray-800">
        <CardContent className="p-6">
          <h3 className="text-lg font-heading font-semibold mb-4">Document Details</h3>
          <div className="lg:flex gap-6 h-[500px]">

            {/* Left side: document content */}
            <div className="flex-1 flex flex-col">
              <div className="bg-background-dark rounded-lg border border-gray-800 overflow-hidden flex flex-col flex-1">
                <div className="p-4 bg-background-surface border-b border-gray-800">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      {getFileIcon(doc.file_type)}
                      <span className="ml-2 font-medium truncate">{doc.name}</span>
                    </div>
                    <Button variant="ghost" size="sm">
                      <FaEye className="mr-2 h-4 w-4" />
                      <span>View Original</span>
                    </Button>
                  </div>
                </div>
                <div
                  className="p-4 overflow-y-auto font-mono text-xs whitespace-pre-line max-w-[50vw] break-words flex-1"
                  style={{ wordBreak: "break-word" }}
                >
                  {doc.full_text ? (<p>{doc.full_text}</p>) : (<p className="text-gray-400 italic">No extracted text available.</p>)}
                </div>
              </div>
            </div>

            {/* Right side: metadata and stats */}
            <div className="w-full lg:w-80 flex flex-col space-y-4">
              {/* Metadata */}
              <div className="bg-background-surface rounded-lg p-4 border border-gray-800">
                <h4 className="font-semibold mb-3">Metadata</h4>
                <div className="space-y-2">
                  {metadata.map((item, index) => (
                    <div key={index} className="flex justify-between text-sm">
                      <span className="text-gray-400">{item.label}:</span>
                      <span className="font-medium">{item.value}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Statistics */}
              <div className="bg-background-surface rounded-lg p-4 border border-gray-800">
                <h4 className="font-semibold mb-3">Processing Statistics</h4>
                <div className="space-y-2">
                  {statistics.map((item, index) => (
                    <div key={index} className="flex justify-between text-sm">
                      <span className="text-gray-400">{item.label}:</span>
                      <span className="font-medium">{item.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
