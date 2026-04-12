import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { AlertTriangle, ArrowRightLeft, Unlink, Trash2, Eye } from "lucide-react";
import { getCategorySingularDisplayName } from "@/components/shared/helpers";

export interface InUseData {
  category: string;
  allowed_mode: "replace" | "detach" | "cascade";
  blueprints: Array<{ id: string; name: string }>;
  resources: Array<{ id: string; name: string; category?: string; type?: string }>;
}

interface ReplacementOption {
  rid: string;
  name: string;
  type: string;
}

interface ResourceInUseModalProps {
  open: boolean;
  onClose: () => void;
  elementName: string;
  inUseData: InUseData;
  replacementOptions: ReplacementOption[];
  isLoadingReplacements: boolean;
  onForceDelete: (mode: "replace" | "detach" | "cascade", replacementId?: string) => Promise<void>;
  onBlueprintClick?: (id: string) => void;
  onResourceClick?: (id: string, category?: string, type?: string) => void;
}

type DeleteMode = "replace" | "detach" | "cascade";

function DependentList({
  items,
  label,
  onItemClick,
}: {
  items: Array<{ id: string; name: string; category?: string; type?: string }>;
  label: string;
  onItemClick?: (item: { id: string; name: string; category?: string; type?: string }) => void;
}) {
  if (items.length === 0) return null;
  return (
    <div className="mt-3">
      <p className="text-sm text-gray-400 mb-1.5">{label}:</p>
      <ul className="space-y-1 max-h-40 overflow-y-auto pr-1">
        {items.map((item) => (
          <li
            key={item.id}
            className="text-sm bg-background-dark rounded px-3 py-1.5 border border-gray-800 flex items-center justify-between"
          >
            <span>{item.name}</span>
            {onItemClick && (
              <button
                type="button"
                aria-label={`View details for ${item.name}`}
                onClick={() => onItemClick(item)}
                className="text-gray-500 hover:text-gray-300 flex-shrink-0 ml-2 rounded-sm p-0.5 transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
              >
                <Eye className="h-3.5 w-3.5" />
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ResourceInUseModal({
  open,
  onClose,
  elementName,
  inUseData,
  replacementOptions,
  isLoadingReplacements,
  onForceDelete,
  onBlueprintClick,
  onResourceClick,
}: ResourceInUseModalProps) {
  const [selectedReplacement, setSelectedReplacement] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState(false);

  const mode = inUseData.allowed_mode;
  const label = getCategorySingularDisplayName(inUseData.category);

  useEffect(() => {
    if (!open) {
      setSelectedReplacement("");
      setIsProcessing(false);
    }
  }, [open]);

  const handleConfirm = async () => {
    setIsProcessing(true);
    try {
      await onForceDelete(mode, mode === "replace" ? selectedReplacement : undefined);
    } finally {
      setIsProcessing(false);
    }
  };

  const canConfirm =
    mode !== "replace" || (selectedReplacement && selectedReplacement.length > 0);

  const hasNoReplacements =
    mode === "replace" && !isLoadingReplacements && replacementOptions.length === 0;

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="bg-background-card border-gray-800 max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-500" />
            Cannot Delete {label}
          </DialogTitle>
          <DialogDescription className="pt-2">
            <span className="font-medium text-gray-200">"{elementName}"</span>{" "}
            is currently in use.
          </DialogDescription>
        </DialogHeader>

        <div className="py-2">
          {mode === "replace" && (
            <ReplaceFlow
              category={inUseData.category}
              label={label}
              resources={inUseData.resources}
              blueprints={inUseData.blueprints}
              replacementOptions={replacementOptions}
              isLoadingReplacements={isLoadingReplacements}
              selectedReplacement={selectedReplacement}
              onSelectReplacement={setSelectedReplacement}
              onBlueprintClick={onBlueprintClick}
              onResourceClick={onResourceClick}
            />
          )}

          {mode === "detach" && (
            <DetachFlow
              label={label}
              resources={inUseData.resources}
              onResourceClick={onResourceClick}
            />
          )}

          {mode === "cascade" && (
            <CascadeFlow
              blueprints={inUseData.blueprints}
              onBlueprintClick={onBlueprintClick}
            />
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={onClose}
            disabled={isProcessing}
            className="border-gray-700 hover:bg-background-dark"
          >
            {hasNoReplacements ? "Close" : "Cancel"}
          </Button>
          {!hasNoReplacements && (
            <ConfirmButton
              mode={mode}
              canConfirm={!!canConfirm}
              isProcessing={isProcessing}
              onClick={handleConfirm}
            />
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ConfirmButton({
  mode,
  canConfirm,
  isProcessing,
  onClick,
}: {
  mode: DeleteMode;
  canConfirm: boolean;
  isProcessing: boolean;
  onClick: () => void;
}) {
  const config = {
    replace: {
      label: "Replace & Delete",
      icon: <ArrowRightLeft className="h-4 w-4 mr-1.5" />,
      className: "bg-primary hover:bg-primary/80",
    },
    detach: {
      label: "Remove & Delete",
      icon: <Unlink className="h-4 w-4 mr-1.5" />,
      className: "bg-red-600 hover:bg-red-700",
    },
    cascade: {
      label: "Delete All",
      icon: <Trash2 className="h-4 w-4 mr-1.5" />,
      className: "bg-red-600 hover:bg-red-700",
    },
  }[mode];

  return (
    <Button
      onClick={onClick}
      disabled={!canConfirm || isProcessing}
      className={`${config.className} text-white`}
    >
      {config.icon}
      {isProcessing ? "Processing..." : config.label}
    </Button>
  );
}

function ReplaceFlow({
  category,
  label,
  resources,
  blueprints,
  replacementOptions,
  isLoadingReplacements,
  selectedReplacement,
  onSelectReplacement,
  onBlueprintClick,
  onResourceClick,
}: {
  category: string;
  label: string;
  resources: InUseData["resources"];
  blueprints: InUseData["blueprints"];
  replacementOptions: ReplacementOption[];
  isLoadingReplacements: boolean;
  selectedReplacement: string;
  onSelectReplacement: (rid: string) => void;
  onBlueprintClick?: (id: string) => void;
  onResourceClick?: (id: string, category?: string, type?: string) => void;
}) {
  return (
    <>
      {blueprints.length > 0 && (
        <DependentList
          items={blueprints}
          label="Used by these workflows"
          onItemClick={
            onBlueprintClick
              ? (item) => onBlueprintClick(item.id)
              : undefined
          }
        />
      )}
      {resources.length > 0 && (
        <DependentList
          items={resources}
          label="Used by these agents"
          onItemClick={
            onResourceClick
              ? (item) => onResourceClick(item.id, item.category, item.type)
              : undefined
          }
        />
      )}

      <div className="mt-4">
        <p className="text-sm text-gray-300 mb-2">
          Choose a replacement {label.toLowerCase()} to swap into all usages:
        </p>

        {replacementOptions.length > 0 ? (
          <Select value={selectedReplacement} onValueChange={onSelectReplacement}>
            <SelectTrigger className="w-full bg-background-dark border-gray-700">
              <SelectValue placeholder={`Select a ${label.toLowerCase()}...`} />
            </SelectTrigger>
            <SelectContent className="bg-background-card border-gray-700">
              {replacementOptions.map((opt) => (
                <SelectItem key={opt.rid} value={opt.rid}>
                  {opt.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : isLoadingReplacements ? (
          <p className="text-sm text-gray-500 italic">Loading available replacements...</p>
        ) : (
          <div className="bg-background-dark border border-gray-800 rounded p-3">
            <p className="text-sm text-gray-400">
              No other {label.toLowerCase()}s available. To remove this {label.toLowerCase()},
              please remove any instances that use it first, or create a new{" "}
              {label.toLowerCase()} to replace this one.
            </p>
          </div>
        )}
      </div>
    </>
  );
}

function DetachFlow({
  label,
  resources,
  onResourceClick,
}: {
  label: string;
  resources: InUseData["resources"];
  onResourceClick?: (id: string, category?: string, type?: string) => void;
}) {
  return (
    <>
      <p className="text-sm text-gray-300">
        This {label.toLowerCase()} will be removed from the following agents. They will
        continue to work without it.
      </p>
      <DependentList
        items={resources}
        label="Used by these agents"
        onItemClick={
          onResourceClick
            ? (item) => onResourceClick(item.id, item.category, item.type)
            : undefined
        }
      />
    </>
  );
}

function CascadeFlow({
  blueprints,
  onBlueprintClick,
}: {
  blueprints: InUseData["blueprints"];
  onBlueprintClick?: (id: string) => void;
}) {
  return (
    <>
      <p className="text-sm text-gray-300">
        Deleting this agent will also delete all workflows that use it.
        This action cannot be undone.
      </p>
      <DependentList
        items={blueprints}
        label="Workflows that will be deleted"
        onItemClick={
          onBlueprintClick
            ? (item) => onBlueprintClick(item.id)
            : undefined
        }
      />
    </>
  );
}
