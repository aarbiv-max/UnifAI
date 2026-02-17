import React from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ArrowRight, ArrowLeftRight } from "lucide-react";

export type EdgeDirection = "unidirectional" | "bidirectional";

interface EdgeDirectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (direction: EdgeDirection) => void;
  sourceNodeLabel: string;
  targetNodeLabel: string;
}

const EdgeDirectionModal: React.FC<EdgeDirectionModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  sourceNodeLabel,
  targetNodeLabel,
}) => {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[400px] bg-gray-900 border-gray-700">
        <DialogHeader>
          <DialogTitle className="text-white">
            Connect Nodes
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <p className="text-sm text-gray-400">
            How should{" "}
            <span className="text-white font-medium">{sourceNodeLabel}</span>
            {" "}and{" "}
            <span className="text-white font-medium">{targetNodeLabel}</span>
            {" "}be connected?
          </p>

          <div className="grid grid-cols-1 gap-3">
            <Button
              variant="outline"
              className="flex items-center justify-start gap-3 h-auto py-3 px-4 border-gray-600 hover:border-gray-400 hover:bg-gray-800 text-left"
              onClick={() => onConfirm("unidirectional")}
            >
              <ArrowRight className="w-5 h-5 text-blue-400 flex-shrink-0" />
              <div>
                <div className="text-sm font-medium text-white">
                  Unidirectional
                </div>
                <div className="text-xs text-gray-400">
                  {sourceNodeLabel} &rarr; {targetNodeLabel}
                </div>
              </div>
            </Button>

            <Button
              variant="outline"
              className="flex items-center justify-start gap-3 h-auto py-3 px-4 border-gray-600 hover:border-gray-400 hover:bg-gray-800 text-left"
              onClick={() => onConfirm("bidirectional")}
            >
              <ArrowLeftRight className="w-5 h-5 text-green-400 flex-shrink-0" />
              <div>
                <div className="text-sm font-medium text-white">
                  Bidirectional
                </div>
                <div className="text-xs text-gray-400">
                  {sourceNodeLabel} &harr; {targetNodeLabel}
                </div>
              </div>
            </Button>
          </div>

          <div className="flex justify-end pt-2">
            <Button
              variant="ghost"
              onClick={onClose}
              className="text-gray-400 hover:text-white"
            >
              Cancel
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default EdgeDirectionModal;
