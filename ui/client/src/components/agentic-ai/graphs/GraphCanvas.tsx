import React, { useState } from "react";
import {
  ReactFlowProvider,
  ReactFlow,
  Node,
  Edge,
  Connection,
  Background,
  Controls,
  NodeTypes,
  EdgeTypes,
  MarkerType,
  ConnectionLineType,
} from "reactflow";
import "reactflow/dist/style.css";
import { Card, CardContent } from "@/components/ui/card";
import { Plus } from "lucide-react";
import CustomNode from "./CustomNode";
import CustomEdge from "./CustomEdge";
import GraphHeader from "./GraphHeader";
import * as yaml from 'js-yaml';

const nodeTypes: NodeTypes = {
  custom: CustomNode,
};

const edgeTypes: EdgeTypes = {
  custom: CustomEdge,
};

interface GraphCanvasProps {
  nodes: Node[];
  edges: Edge[];
  yamlFlow?: any;
  onNodesChange: (changes: any[]) => void;
  onEdgesChange: (changes: any[]) => void;
  onConnect: (params: Connection) => void;
  onDrop: (event: React.DragEvent) => void;
  onDragOver: (event: React.DragEvent) => void;
  onClearGraph: () => void;
  onSaveGraph: () => void;
  onRearrangeGraph: () => void;
  onDeleteEdge?: (edgeId: string) => void;
  onBack?: () => void;
  onAttachCondition?: (nodeId: string, condition: any) => void;
  onRemoveCondition?: (nodeId: string, conditionRid: string) => void;
  isGraphValid?: boolean;
}

const GraphCanvas: React.FC<GraphCanvasProps> = ({
  nodes,
  edges,
  yamlFlow,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onDrop,
  onDragOver,
  onClearGraph,
  onSaveGraph,
  onRearrangeGraph,
  onDeleteEdge,
  onBack,
  onAttachCondition,
  onRemoveCondition,
  isGraphValid = false,
}) => {
  const [showYamlDebug, setShowYamlDebug] = useState(false);

  const parallelOffsets = new Map<string, number>();
  const parallelTotals = new Map<string, number>();
  const groupedEdges = new Map<string, Edge[]>();

  edges.forEach((edge) => {
    const key = [edge.source, edge.target].sort().join("::");
    const group = groupedEdges.get(key) || [];
    group.push(edge);
    groupedEdges.set(key, group);
  });

  groupedEdges.forEach((group) => {
    const ordered = [...group].sort((a, b) => a.id.localeCompare(b.id));
    const total = ordered.length;
    ordered.forEach((edge, index) => {
      const offset = index - (total - 1) / 2;
      parallelOffsets.set(edge.id, offset);
      parallelTotals.set(edge.id, total);
    });
  });

  return (
    <div className="flex-1 relative">
      <Card className="bg-background-card shadow-card border-gray-800 h-full">
        <GraphHeader
          onClearGraph={onClearGraph}
          onSaveGraph={onSaveGraph}
          onRearrangeGraph={onRearrangeGraph}
          onBack={onBack}
          isGraphValid={isGraphValid}
        />
        <CardContent className="p-0 h-full relative">
          {/* YAML Debug Panel */}
          {showYamlDebug && yamlFlow && (
            <div className="absolute top-4 right-4 z-50 bg-gray-900 border border-gray-700 rounded-lg p-4 max-w-md max-h-96 overflow-auto">
              <div className="flex justify-between items-center mb-2">
                <h3 className="text-sm font-medium text-white">YAML Flow State</h3>
                <button
                  onClick={() => setShowYamlDebug(false)}
                  className="text-gray-400 hover:text-white"
                >
                  ×
                </button>
              </div>
              <pre className="text-xs text-gray-300 overflow-auto">
                {yaml.dump(yamlFlow, { indent: 2, lineWidth: -1 })}
              </pre>
            </div>
          )}

          {/* YAML Debug Toggle Button */}
          <button
            onClick={() => setShowYamlDebug(!showYamlDebug)}
            className="absolute top-4 right-4 z-40 bg-gray-800 hover:bg-gray-700 text-white px-3 py-1 text-xs rounded border border-gray-600"
          >
            {showYamlDebug ? 'Hide' : 'Show'} YAML
          </button>

          <div className="h-full" style={{ height: "calc(100vh - 180px)" }}>
            <ReactFlowProvider>
              <ReactFlow
                nodes={nodes}
                edges={edges.map((edge) => ({
                  ...edge,
                  type: edge.type || "custom",
                  data: {
                    ...edge.data,
                    onDelete: onDeleteEdge,
                    parallelOffset: parallelOffsets.get(edge.id) ?? 0,
                    parallelTotal: parallelTotals.get(edge.id) ?? 1,
                  },
                }))}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onDrop={onDrop}
                onDragOver={onDragOver}
                nodeTypes={nodeTypes}
                edgeTypes={edgeTypes}
                fitView
                defaultViewport={{ x: 0, y: 0, zoom: 0.33 }}
                connectionLineType={ConnectionLineType.SmoothStep}
                defaultEdgeOptions={{
                  type: "custom",
                  animated: true,
                  style: { stroke: "#8A2BE2", strokeWidth: 2 },
                  markerEnd: {
                    type: MarkerType.ArrowClosed,
                    width: 20,
                    height: 20,
                    color: "#8A2BE2",
                  },
                }}
              >
                <Background color="#aaa" gap={16} />
                <Controls />
              </ReactFlow>
            </ReactFlowProvider>

            {/* Drop zone overlay when empty */}
            {nodes.length === 0 && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="text-center">
                  <Plus className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                  <h3 className="mt-2 text-sm font-medium text-gray-300">
                    No nodes yet
                  </h3>
                  <p className="mt-1 text-sm text-gray-400">
                    Drag building blocks from the sidebar to get started
                  </p>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default GraphCanvas;