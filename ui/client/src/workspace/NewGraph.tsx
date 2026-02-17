import React, { useState, useMemo } from "react";
import { useGraphLogic, SavedBlueprintInfo } from "@/hooks/use-graph-logic";
import GraphCanvas from "@/components/agentic-ai/graphs/GraphCanvas";
import BuildingBlocksSidebar from "./BuildingBlocksSidebar";
import ConditionalEdgeModal from "@/components/agentic-ai/graphs/ConditionalEdgeModal";
import EdgeDirectionModal from "@/components/agentic-ai/graphs/EdgeDirectionModal";
import GraphValidationPanel from "@/components/agentic-ai/graphs/GraphValidationPanel";
import SaveBlueprintModal from "@/components/agentic-ai/graphs/SaveBlueprintModal";

interface NewGraphProps {
  onBack?: (savedBlueprint?: SavedBlueprintInfo) => void;
}

export default function NewGraph({ onBack }: NewGraphProps) {
  const {
    canvasNodes,
    canvasEdges,
    buildingBlocksData,
    orchestratorsData,
    conditionsData,
    allBlocksData,
    isLoadingBlocks,
    yamlFlow,

    addNode,
    deleteNode,
    deleteEdge,

    connectionSource,
    handleNodeClick,
    cancelConnection,

    edgeDirectionModal,
    handleEdgeDirectionConfirm,
    handleEdgeDirectionCancel,

    conditionalEdgeModal,
    handleConditionalEdgeConfirm,
    handleConditionalEdgeCancel,

    attachConditionToNode,
    removeConditionFromNode,

    onDragStart,
    onDragEnd,
    isDraggingCondition,

    clearGraph,
    saveGraph,

    isGraphValid,
    validationResult,
    fixSuggestions,
    isValidating,
    validateGraph,
    isSaving,
  } = useGraphLogic({ onSaveComplete: onBack });

  const [saveModalOpen, setSaveModalOpen] = useState(false);

  // Track which building blocks are currently used on the canvas
  const usedElementIds = useMemo(() => {
    const usedIds = new Set<string>();

    canvasNodes.forEach((node) => {
      if (node.workspaceData?.rid) {
        const matchingBlock = [
          ...buildingBlocksData,
          ...orchestratorsData,
          ...conditionsData,
        ].find((block) => block.workspaceData?.rid === node.workspaceData?.rid);
        if (matchingBlock) usedIds.add(matchingBlock.id);
      }

      if (node.conditions && Array.isArray(node.conditions)) {
        node.conditions.forEach((condition) => {
          if (condition.workspaceData?.rid) {
            const matchingCondition = conditionsData.find(
              (block) => block.workspaceData?.rid === condition.workspaceData?.rid,
            );
            if (matchingCondition) usedIds.add(matchingCondition.id);
          }
        });
      }
    });

    return usedIds;
  }, [canvasNodes, buildingBlocksData, orchestratorsData, conditionsData]);

  // Labels for direction modal
  const sourceLabel = useMemo(() => {
    const n = canvasNodes.find((n) => n.id === edgeDirectionModal.sourceNodeId);
    return n?.label || edgeDirectionModal.sourceNodeId;
  }, [canvasNodes, edgeDirectionModal.sourceNodeId]);

  const targetLabel = useMemo(() => {
    const n = canvasNodes.find((n) => n.id === edgeDirectionModal.targetNodeId);
    return n?.label || edgeDirectionModal.targetNodeId;
  }, [canvasNodes, edgeDirectionModal.targetNodeId]);

  return (
    <div className="h-full max-h-[calc(100vh-100px)] flex bg-background overflow-hidden">
      {/* Sidebar */}
      <div className="w-80 h-full">
        <BuildingBlocksSidebar
          buildingBlocks={buildingBlocksData}
          orchestrators={orchestratorsData}
          conditions={conditionsData}
          isLoading={isLoadingBlocks}
          onDragStart={onDragStart}
          onDragEnd={onDragEnd}
          usedElementIds={usedElementIds}
        />
      </div>

      {/* Main Canvas */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <GraphCanvas
          canvasNodes={canvasNodes}
          canvasEdges={canvasEdges}
          allBlocks={allBlocksData}
          yamlFlow={yamlFlow}
          connectionSource={connectionSource}
          onNodeClick={handleNodeClick}
          onCancelConnection={cancelConnection}
          onAddNode={addNode}
          onDeleteNode={deleteNode}
          onDeleteEdge={deleteEdge}
          onAttachCondition={attachConditionToNode}
          onRemoveCondition={removeConditionFromNode}
          onClearGraph={clearGraph}
          onSaveGraph={() => setSaveModalOpen(true)}
          onBack={onBack}
          isGraphValid={isGraphValid}
          isDraggingCondition={isDraggingCondition}
          onValidate={validateGraph}
          isValidating={isValidating}
        />
      </div>

      {/* Validation Panel */}
      <div className="w-80 h-full">
        <GraphValidationPanel
          validationResult={validationResult}
          fixSuggestions={fixSuggestions}
          isValidating={isValidating}
        />
      </div>

      {/* Edge Direction Modal */}
      <EdgeDirectionModal
        isOpen={edgeDirectionModal.isOpen}
        onClose={handleEdgeDirectionCancel}
        onConfirm={handleEdgeDirectionConfirm}
        sourceNodeLabel={sourceLabel}
        targetNodeLabel={targetLabel}
      />

      {/* Conditional Edge Modal */}
      <ConditionalEdgeModal
        isOpen={conditionalEdgeModal.isOpen}
        onClose={handleConditionalEdgeCancel}
        onConfirm={handleConditionalEdgeConfirm}
        sourceNodeId={conditionalEdgeModal.sourceNodeId}
        targetNodeId={conditionalEdgeModal.targetNodeId}
        conditionType={conditionalEdgeModal.conditionType}
        existingBranches={conditionalEdgeModal.existingBranches}
      />

      {/* Save Blueprint Modal */}
      <SaveBlueprintModal
        isOpen={saveModalOpen}
        onClose={() => setSaveModalOpen(false)}
        onSave={saveGraph}
        isLoading={isSaving}
      />
    </div>
  );
}
