import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { AlertTriangle, Unlink } from "lucide-react";
import type { RetrieverUsage } from "@/api/docs";

interface DocInUseModalProps {
  open: boolean;
  onClose: () => void;
  docNames: string[];
  retrievers: RetrieverUsage[];
  currentUser: string;
  onConfirmDelete: () => Promise<void>;
}

export function DocInUseModal({
  open,
  onClose,
  docNames,
  retrievers,
  currentUser,
  onConfirmDelete,
}: DocInUseModalProps) {
  const [isProcessing, setIsProcessing] = useState(false);

  const ownRetrievers = retrievers.filter((r) => r.user_id === currentUser);
  const otherRetrievers = retrievers.filter((r) => r.user_id !== currentUser);

  const isSingleDoc = docNames.length === 1;
  const docLabel = isSingleDoc
    ? `"${docNames[0]}"`
    : `${docNames.length} selected documents`;

  const handleConfirm = async () => {
    setIsProcessing(true);
    try {
      await onConfirmDelete();
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && !isProcessing && onClose()}>
      <DialogContent className="bg-background-card border-gray-800 max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-500" />
            Document In Use
          </DialogTitle>
          <DialogDescription className="pt-2">
            {docLabel} {isSingleDoc ? "is" : "are"} currently referenced by{" "}
            {retrievers.length === 1 ? "a retriever" : "retrievers"}.
            Deleting will remove {isSingleDoc ? "it" : "them"} from their
            document lists.
          </DialogDescription>
        </DialogHeader>

        <div className="py-2 space-y-3">
          {ownRetrievers.length > 0 && (
            <div>
              <p className="text-sm text-gray-400 mb-1.5">Your retrievers:</p>
              <ul className="space-y-1 max-h-40 overflow-y-auto pr-1">
                {ownRetrievers.map((r) => (
                  <li
                    key={r.rid}
                    className="text-sm bg-background-dark rounded px-3 py-1.5 border border-gray-800"
                  >
                    {r.name}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {otherRetrievers.length > 0 && (
            <div className="bg-background-dark border border-gray-800 rounded p-3">
              <p className="text-sm text-gray-300">
                Also used by{" "}
                <span className="font-medium text-gray-200">
                  {otherRetrievers.length}
                </span>{" "}
                {otherRetrievers.length === 1 ? "retriever" : "retrievers"} belonging
                to other users.
              </p>
            </div>
          )}

          <p className="text-sm text-yellow-400/80 mt-2">
            Proceeding will remove{" "}
            {isSingleDoc ? "this document" : "these documents"} from{" "}
            {retrievers.length === 1 ? "this retriever's" : "these retrievers'"}{" "}
            document list and then delete{" "}
            {isSingleDoc ? "the document" : "the documents"}.
          </p>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={onClose}
            disabled={isProcessing}
            className="border-gray-700 hover:bg-background-dark"
          >
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={isProcessing}
            className="bg-red-600 hover:bg-red-700 text-white"
          >
            <Unlink className="h-4 w-4 mr-1.5" />
            {isProcessing
              ? "Processing..."
              : `Remove & Delete`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
