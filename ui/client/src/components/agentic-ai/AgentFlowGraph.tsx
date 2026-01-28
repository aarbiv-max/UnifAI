import React, { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StreamingDataProvider } from "@/components/agentic-ai/StreamingDataContext";
import { FlowObject } from "./graphs/interfaces";
import WorkflowsPanel from "./WorkflowsPanel";
import { BlueprintValidationResult } from "@/types/validation";

// Create a ReactFlow provider wrapper
import { ReactFlowProvider } from "reactflow";

const DEFAULT_GRAPH_PROPS = {
  showControls: true,
  showMiniMap: false,
  showBackground: true,
  interactive: true,
  isLiveRequest: false,
  useSmartEdges: true,
  autoZoomOut: false,
  showLegend: true,
  legendClassName: "absolute bottom-3 right-3 z-40",
  legendMarkerIdPrefix: "agentic-workflows-legend",
} as const;

type AgentFlowGraphProps = {
  selectedFlow: FlowObject | null;
  setSelectedFlow: (flow: FlowObject | null) => void;
  onValidationChange?: (isValid: boolean, validationResult: BlueprintValidationResult | null, isValidating: boolean) => void;
  graphProps?: {
    showControls?: boolean;
    showMiniMap?: boolean;
    showBackground?: boolean;
    interactive?: boolean;
    isLiveRequest?: boolean;
    useSmartEdges?: boolean;
    autoZoomOut?: boolean;
    showLegend?: boolean;
    legendClassName?: string;
    legendMarkerIdPrefix?: string;
  };
};

export default function AgentFlowGraph({
  selectedFlow,
  setSelectedFlow,
  onValidationChange,
  graphProps,
}: AgentFlowGraphProps): React.ReactElement {
  
  const handleFlowSelect = (flow: FlowObject | null): void => {
    setSelectedFlow(flow);
  };

  const handleFlowDelete = (flow: FlowObject): void => {
    // If the deleted flow was selected, clear the selection
    if (selectedFlow?.id === flow.id) {
      setSelectedFlow(null);
    }
  };

  // Memoize merged props to ensure referential stability
  const mergedGraphProps = useMemo(
    () => ({ ...DEFAULT_GRAPH_PROPS, ...(graphProps || {}) }),
    [graphProps]
  );

  return (
    <Card className="bg-background-card shadow-card border-gray-800">
      <CardHeader className="py-4 px-6 flex flex-row justify-between items-center">
        <CardTitle className="text-lg font-heading">
          Agent Workflow Visualization
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0" style={{ height: "73.5vh" }}>
        <StreamingDataProvider>
          <ReactFlowProvider>
            <WorkflowsPanel
              selectedFlow={selectedFlow}
              onFlowSelect={handleFlowSelect}
              onFlowDelete={handleFlowDelete}
              onValidationChange={onValidationChange}
              showActiveStatus={true}
              showDeleteButton={true}
              useResolvedEndpoint={true}
              height="100%"
              graphProps={mergedGraphProps}
            />
          </ReactFlowProvider>
        </StreamingDataProvider>
      </CardContent>
    </Card>
  );
}