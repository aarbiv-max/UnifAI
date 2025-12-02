import React, { useState, useMemo, useCallback } from "react";
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
import BidirectionalEdge from "./BidirectionalEdge";
import GraphHeader from "./GraphHeader";
import * as yaml from 'js-yaml';
import { useTheme } from "@/contexts/ThemeContext";
import { getPaletteColor } from "@/lib/colorUtils";

const nodeTypes: NodeTypes = {
  custom: CustomNode,
};

const edgeTypes: EdgeTypes = {
  custom: CustomEdge,
  bidirectional: BidirectionalEdge, // Only used when one edge is conditional
};

// Helper function to detect and replace bidirectional edge pairs with a single bidirectional edge
const processBidirectionalEdges = (edges: Edge[]): Edge[] => {
  if (!edges || edges.length === 0) return [];
  
  const edgeMap = new Map<string, Edge[]>();
  const processedEdges: Edge[] = [];

  // First pass: collect edges that should be skipped (already bidirectional)
  // Note: We now include conditional edges in bidirectional detection
  const regularEdges: Edge[] = [];
  const conditionalEdges: Edge[] = [];
  
  edges.forEach(edge => {
    // Skip edges that are already bidirectional
    if (edge.id.startsWith('bidirectional-')) {
      processedEdges.push(edge);
      return;
    }
    
    // Separate conditional and regular edges for processing
    if (edge.id.includes('-branch-')) {
      conditionalEdges.push(edge);
    } else {
      regularEdges.push(edge);
    }
  });
    
  // Second pass: group ALL edges (regular + conditional) by node pairs (regardless of direction)
  // This allows bidirectional detection between regular edges, conditional edges, or mixed
  const allEdgesForPairing = [...regularEdges, ...conditionalEdges];
  
  allEdgesForPairing.forEach(edge => {
    // Create canonical key (smaller node ID first) to identify the pair
    const node1 = edge.source < edge.target ? edge.source : edge.target;
    const node2 = edge.source < edge.target ? edge.target : edge.source;
    const canonicalKey = `${node1}-${node2}`;
    
    if (!edgeMap.has(canonicalKey)) {
      edgeMap.set(canonicalKey, []);
    }
    edgeMap.get(canonicalKey)!.push(edge);
  });

  // Third pass: process each edge group
  edgeMap.forEach((edgeGroup, canonicalKey) => {
    if (edgeGroup.length === 2) {
      // Bidirectional pair detected - replace with a single bidirectional edge
      const [edge1, edge2] = edgeGroup;
      
      // Verify they are actually opposite directions
      const isBidirectional = 
        (edge1.source === edge2.target && edge1.target === edge2.source) ||
        (edge1.target === edge2.source && edge1.source === edge2.target);
      
      if (isBidirectional) {
        // Check if at least one edge is conditional (has -branch- in ID)
        const edge1IsConditional = edge1.id.includes('-branch-');
        const edge2IsConditional = edge2.id.includes('-branch-');
        const hasConditionalEdge = edge1IsConditional || edge2IsConditional;
        
        // Only create bidirectional edge if one of the edges is conditional
        if (hasConditionalEdge) {
          // Create a single bidirectional edge using the first edge's source/target
          const bidirectionalEdge: Edge = {
        ...edge1,
            id: `bidirectional-${edge1.source}-${edge1.target}`, // New unique ID
            type: 'bidirectional',
        data: {
          ...edge1.data,
              bidirectional: true,
              originalEdgeIds: [edge1.id, edge2.id], // Keep track of original edges for deletion
              hasConditional: true, // Mark that this bidirectional edge involves a conditional
        },
        style: {
              // Color will be set by BidirectionalEdge component using primary palette
              strokeWidth: 4, // Thicker than regular edges
            },
            // Remove markerEnd since we'll have arrows on both ends
            markerEnd: undefined,
          };
          
          processedEdges.push(bidirectionalEdge);
        } else {
          // Both edges are regular - keep them as separate edges
          edgeGroup.forEach(edge => {
            processedEdges.push({
              ...edge,
              type: edge.type === 'default' ? 'custom' : (edge.type || 'custom'),
            });
          });
        }
      } else {
        // Not actually bidirectional - add both as separate edges
        edgeGroup.forEach(edge => {
          // Conditional edges should use 'custom' type, regular edges too
          const edgeType = edge.id.includes('-branch-') 
            ? (edge.type === 'default' ? 'custom' : (edge.type || 'custom'))
            : (edge.type === 'default' ? 'custom' : (edge.type || 'custom'));
          processedEdges.push({
            ...edge,
            type: edgeType,
          });
        });
      }
    } else if (edgeGroup.length === 1) {
      // Single directional edge - keep as is, ensure it uses 'custom' type if it was 'default'
      const edge = edgeGroup[0];
      const edgeType = edge.id.includes('-branch-')
        ? (edge.type === 'default' ? 'custom' : (edge.type || 'custom'))
        : (edge.type === 'default' ? 'custom' : (edge.type || 'custom'));
      processedEdges.push({
        ...edge,
        type: edgeType,
      });
    } else if (edgeGroup.length > 2) {
      // More than 2 edges between same nodes - add all as separate edges
      edgeGroup.forEach(edge => {
        const edgeType = edge.id.includes('-branch-')
          ? (edge.type === 'default' ? 'custom' : (edge.type || 'custom'))
          : (edge.type === 'default' ? 'custom' : (edge.type || 'custom'));
        processedEdges.push({
          ...edge,
          type: edgeType,
        });
      });
    }
  });

  return processedEdges;
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
  onDeleteEdge,
  onBack,
  onAttachCondition,
  onRemoveCondition,
  isGraphValid = false,
}) => {
  const [showYamlDebug, setShowYamlDebug] = useState(false);
  const { primaryHex } = useTheme();
  
  // Get primary color for edges - use useMemo to recalculate when primaryHex changes
  const primaryEdgeColor = useMemo(() => getPaletteColor(primaryHex, 0, 6), [primaryHex]);
  
  // Process edges to detect and transform bidirectional connections
  // This must run on every edges change to detect new bidirectional pairs
  const processedEdges = useMemo(() => {
    if (!edges || edges.length === 0) return [];
    // Process edges to detect bidirectional pairs
    const result = processBidirectionalEdges(edges);
    return result;
  }, [edges]);

  return (
    <div className="flex-1 relative">
      <Card className="bg-background-card shadow-card border-gray-800 h-full">
        <GraphHeader
          onClearGraph={onClearGraph}
          onSaveGraph={onSaveGraph}
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
                edges={processedEdges.map(edge => {
                  // Ensure bidirectional edges keep their type, others default to 'custom'
                  const edgeType = edge.type === 'bidirectional' ? 'bidirectional' : (edge.type || 'custom');
                  return {
                  ...edge,
                    type: edgeType,
                  data: {
                    ...edge.data,
                    onDelete: onDeleteEdge,
                  }
                  };
                })}
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
                  style: { stroke: primaryEdgeColor, strokeWidth: 2 },
                  markerEnd: {
                    type: MarkerType.ArrowClosed,
                    width: 20,
                    height: 20,
                    color: primaryEdgeColor,
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