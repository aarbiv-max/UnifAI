import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Trash2, Users, Pencil, Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/contexts/AuthContext";
import { useShared } from "@/contexts/SharedContext";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import SimpleTooltip from "@/components/shared/SimpleTooltip";
import { FlowObject } from "./graphs/interfaces";
import GraphDisplay from "./graphs/GraphDisplay";
import { fetchActiveSessions } from "@/api/agentic";
import { deleteBlueprint, fetchResolvedBlueprint } from "@/api/blueprints";
import ShareWorkflow from "./ShareWorkflow";
import { BlueprintValidationResult } from "@/types/validation";
import { useBlueprintValidation } from "@/hooks/use-blueprint-validation";
import {
  useWorkflowSummariesList,
  WORKFLOW_LIST_PAGE_SIZE,
} from "@/hooks/use-workflow-summaries-list";
import ChatSessionsPager from "@/components/agentic-ai/ChatSessionsPager";

export interface WorkflowsPanelProps {
  selectedFlow: FlowObject | null;
  onFlowSelect: (flow: FlowObject | null) => void;
  onFlowDelete?: (flow: FlowObject) => void;
  onFlowEdit?: (flow: FlowObject) => void;
  onValidationChange?: (isValid: boolean, validationResult: BlueprintValidationResult | null, isValidating: boolean) => void;
  showActiveStatus?: boolean;
  showDeleteButton?: boolean;
  showEditButton?: boolean;
  className?: string;
  height?: string;
  graphProps?: {
    showBackground?: boolean;
    interactive?: boolean;
  };
}

export default function WorkflowsPanel({
  selectedFlow,
  onFlowSelect,
  onFlowDelete,
  onFlowEdit,
  onValidationChange,
  showActiveStatus = false,
  showDeleteButton = false,
  showEditButton = false,
  className = "",
  height = "100%",
  graphProps = {
    showBackground: true,
    interactive: true,
  },
}: WorkflowsPanelProps): React.ReactElement {
  const [activeFlowIds, setActiveFlowIds] = useState<string[]>([]);
  const [activeIdsLoading, setActiveIdsLoading] = useState(showActiveStatus);
  const [showDeleteModal, setShowDeleteModal] = useState<boolean>(false);
  const [flowToDelete, setFlowToDelete] = useState<FlowObject | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [selectedBlueprintData, setSelectedBlueprintData] = useState<{
    specDict: any;
    sharingEnabled: boolean;
  } | null>(null);
  
  const { user } = useAuth();
  const { openShareForItem } = useShared();

  const userId = user?.username || "default";
  const flows = useWorkflowSummariesList(userId);

  const panelBlockingLoading =
    flows.isLoading || (showActiveStatus && activeIdsLoading);
  
  // Blueprint validation hook
  const {
    isValidating,
    validationResults,
    isValid,
    validateBlueprint: validateSelectedBlueprint,
    clearValidation,
  } = useBlueprintValidation({
    activeBlueprintId: selectedFlow?.id ?? null,
    onValidationChange,
    showToastOnFailure: true,
  });

  useEffect(() => {
    if (!showActiveStatus) {
      setActiveIdsLoading(false);
      return;
    }
    let cancelled = false;
    setActiveIdsLoading(true);
    fetchActiveSessions(userId)
      .then((ids) => {
        if (!cancelled) setActiveFlowIds(ids || []);
      })
      .catch(() => {
        if (!cancelled) setActiveFlowIds([]);
      })
      .finally(() => {
        if (!cancelled) setActiveIdsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [userId, showActiveStatus]);

  useEffect(() => {
    if (flows.isLoading) return;
    if (flows.currentPage !== 0) return;
    if (flows.total === 0) return;
    const first = flows.displayedItems[0];
    if (!first || selectedFlow) return;
    onFlowSelect(first);
  }, [
    flows.isLoading,
    flows.total,
    flows.displayedItems,
    flows.currentPage,
    selectedFlow,
    onFlowSelect,
  ]);

  // Trigger validation when selected flow changes
  useEffect(() => {
    if (selectedFlow?.id) {
      validateSelectedBlueprint(selectedFlow.id);
    } else {
      // Clear validation state when no flow is selected
      clearValidation();
    }
  }, [selectedFlow?.id, validateSelectedBlueprint, clearValidation]);

  // Fetch blueprint data (spec_dict + metadata) when selected flow changes.
  // This consolidates API calls - data is fetched once and passed to child components.
  // A `cancelled` flag prevents stale responses from overwriting state when the
  // user switches flows quickly.
  useEffect(() => {
    if (!selectedFlow?.id) {
      setSelectedBlueprintData(null);
      return;
    }

    let cancelled = false;
    // Clear previous data immediately so the UI shows a loading state
    // instead of the previous flow's graph while the new fetch is in-flight.
    setSelectedBlueprintData(null);

    const fetchBlueprintData = async () => {
      try {
        const userId = user?.username || 'default';
        const blueprint = await fetchResolvedBlueprint(selectedFlow.id, userId);
        if (cancelled) return;
        if (blueprint) {
          setSelectedBlueprintData({
            specDict: blueprint.spec_dict,
            sharingEnabled: blueprint.metadata?.usageScope === "public",
          });
        }
      } catch (error) {
        if (cancelled) return;
        console.error("Error fetching blueprint data:", error);
        setSelectedBlueprintData(null);
      }
    };

    fetchBlueprintData();
    return () => { cancelled = true; };
  }, [selectedFlow?.id, user?.username]);

  const handleFlowSelect = (flow: FlowObject): void => {
    onFlowSelect(flow);
  };

  const isFlowActive = (flowId: string): boolean => {
    return activeFlowIds.includes(flowId);
  };

  const handleDeleteClick = (flow: FlowObject, event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent flow selection when clicking delete
    setFlowToDelete(flow);
    setShowDeleteModal(true);
  };

  const handleEditClick = (flow: FlowObject, event: React.MouseEvent) => {
    event.stopPropagation();
    if (onFlowEdit) {
      onFlowEdit(flow);
    }
  };

  const handleShareClick = (flow: FlowObject, event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent flow selection when clicking share
    openShareForItem({
      itemKind: 'blueprint',
      itemId: flow.id,
      itemName: flow.name,
    });
  };

  const handleDeleteConfirm = async () => {
    if (!flowToDelete) return;

    setIsDeleting(true);
    try {
      await deleteBlueprint(flowToDelete.id);

      flows.removeItemById(flowToDelete.id);

      // If the deleted flow was selected, clear the selection
      if (selectedFlow?.id === flowToDelete.id) {
        onFlowSelect(null);
      }
      
      // Call the optional onFlowDelete callback
      if (onFlowDelete) {
        onFlowDelete(flowToDelete);
      }
      
      setShowDeleteModal(false);
      setFlowToDelete(null);
    } catch (error) {
      console.error('Error deleting blueprint:', error);
      // Handle error (we can consider show a toast notification here)
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setShowDeleteModal(false);
    setFlowToDelete(null);
  };

  if (
    panelBlockingLoading && flows.total === 0 && !flows.listLoadError
  ) {
    return (
      <div className={`flex h-full overflow-hidden ${className}`} style={{ height }}>
        <div className="w-1/3 border-r border-gray-800 bg-background-dark flex flex-col min-h-0">
          <div className="py-3 px-4 border-b border-gray-800 bg-background-surface flex-shrink-0">
            <h3 className="text-sm font-medium">Available Workflows</h3>
          </div>
          <div className="flex-1 flex items-center justify-center overflow-hidden">
            <div className="text-gray-400">Loading flows...</div>
          </div>
        </div>
        <div className="flex-grow min-h-0 overflow-hidden">
          <div className="flex items-center justify-center h-full text-gray-400">
            Loading...
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className={`flex h-full overflow-hidden ${className}`} style={{ height }}>
        {/* Available Workflows Sidebar */}
        <div className="w-1/3 border-r border-gray-800 bg-background-dark flex flex-col min-h-0 relative">
          <div className="py-3 px-4 border-b border-gray-800 bg-background-surface flex-shrink-0 space-y-2">
            <h3 className="text-sm font-medium">Available Workflows ({flows.total})</h3>
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400 pointer-events-none" />
              <Input
                placeholder="Search workflows..."
                value={flows.searchQuery}
                onChange={(e) => flows.setSearchQuery(e.target.value)}
                className="h-8 pl-8 pr-8 text-xs bg-background-dark border-gray-700 focus:border-primary"
              />
              {flows.searchQuery && (
                <SimpleTooltip content={<p>Clear search</p>}>
                  <button
                    type="button"
                    aria-label="Clear search"
                    onClick={() => flows.setSearchQuery("")}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </SimpleTooltip>
              )}
            </div>
          </div>
          <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
            <div className="flex-1 overflow-y-auto py-2 relative">
            {flows.listLoadError ? (
              <div className="flex items-center justify-center py-8 px-4">
                <div className="text-red-400 text-sm text-center">{flows.listLoadError}</div>
              </div>
            ) : flows.total === 0 && !flows.isLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="text-gray-400 text-sm text-center px-4">
                  {flows.debouncedSearch
                    ? `No workflows match "${flows.debouncedSearch}"`
                    : "No flows available"}
                </div>
              </div>
            ) : (
              flows.displayedItems.map((flow) => (
                <motion.div
                  key={flow.id}
                  className={`px-4 py-2 border-l-2 cursor-pointer ${
                    selectedFlow?.id === flow.id
                      ? "border-primary bg-primary/20"
                      : "border-transparent hover:bg-background-surface"
                  }`}
                  onClick={() => handleFlowSelect(flow)}
                  whileHover={{ x: 2 }}
                  transition={{ duration: 0.1 }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center min-w-0 flex-1">
                      {flow.icon}
                      <span className="text-sm font-medium truncate">{flow.name}</span>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {showActiveStatus && isFlowActive(flow.id) && (
                        <span className="text-xs bg-primary text-white px-2 py-1 rounded-full">
                          Active
                        </span>
                      )}
                      {showEditButton && (
                        <SimpleTooltip content={<p>Edit this workflow</p>}>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0 hover:bg-primary/20 hover:text-primary"
                            onClick={(e) => handleEditClick(flow, e)}
                          >
                            <Pencil className="h-3 w-3" />
                          </Button>
                        </SimpleTooltip>
                      )}
                      <SimpleTooltip content={<p>Share this workflow</p>}>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0 hover:bg-blue-500/20 hover:text-blue-400"
                          onClick={(e) => handleShareClick(flow, e)}
                        >
                          <Users className="h-3 w-3" />
                        </Button>
                      </SimpleTooltip>
                      {showDeleteButton && (
                        <SimpleTooltip content={<p>Delete this workflow</p>}>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0 hover:bg-red-500/20 hover:text-red-400"
                            onClick={(e) => handleDeleteClick(flow, e)}
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </SimpleTooltip>
                      )}
                    </div>
                  </div>
                  <p className="text-xs text-gray-400 mt-1 truncate">
                    {flow.description}
                  </p>
                </motion.div>
              ))
            )}
            </div>
            <ChatSessionsPager
              pageSize={WORKFLOW_LIST_PAGE_SIZE}
              total={flows.total}
              currentPage={flows.currentPage}
              maxPageIndex={flows.maxPageIndex}
              onPrev={flows.goToPrevPage}
              onNext={flows.goToNextPage}
              disabled={flows.isCurrentPageLoading}
            />
          </div>
        </div>

        {/* Graph Visualization and Share Section */}
        <div className="flex-grow min-h-0 overflow-hidden flex flex-col">
          {selectedFlow ? (
            <>
              {/* Share Section */}
              <div className="border-b border-gray-800 bg-background-surface p-4">
                <ShareWorkflow 
                  blueprintId={selectedFlow.id} 
                  isValid={isValid}
                  isValidating={isValidating}
                  initialSharingEnabled={selectedBlueprintData?.sharingEnabled ?? false}
                />
              </div>
            {selectedBlueprintData?.specDict ? (
              <GraphDisplay
                blueprintId={selectedFlow.id}
                specDict={selectedBlueprintData.specDict}
                height="100%"
                showBackground={graphProps?.showBackground}
                interactive={graphProps?.interactive}
                centerInView={true}
                animated={true}
                validationResults={validationResults}
                isValidating={isValidating}
              />
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400">
                Loading graph...
              </div>
            )}
            </>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400">
              Select a flow to view its visualization
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteButton && (
        <Dialog open={showDeleteModal} onOpenChange={setShowDeleteModal}>
          <DialogContent className="bg-background-card border-gray-800">
            <DialogHeader>
              <DialogTitle>Delete Flow</DialogTitle>
              <DialogDescription>
                Are you sure you want to delete "{flowToDelete?.name}"?
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={handleDeleteCancel}
                disabled={isDeleting}
                className="bg-background-dark border-gray-700 hover:bg-background-surface"
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleDeleteConfirm}
                disabled={isDeleting}
              >
                {isDeleting ? "Deleting..." : "Confirm"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
}
