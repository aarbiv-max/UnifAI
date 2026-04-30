import React from "react";
import { FileText } from "lucide-react";
import type { FileReference } from "./types";

interface ChatAttachmentsProps {
  files: FileReference[];
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ChatAttachments({ files }: ChatAttachmentsProps) {
  if (!files || files.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1 mt-1">
      {files.map((ref, idx) => (
        <span
          key={idx}
          className="inline-flex items-center gap-1 rounded-md bg-muted/60 px-2 py-0.5 text-xs text-muted-foreground"
        >
          <FileText className="h-3 w-3 shrink-0" />
          <span className="truncate max-w-[120px]">{ref.display_name}</span>
          <span className="text-[10px] opacity-60">
            ({formatSize(ref.size_bytes)})
          </span>
        </span>
      ))}
    </div>
  );
}
