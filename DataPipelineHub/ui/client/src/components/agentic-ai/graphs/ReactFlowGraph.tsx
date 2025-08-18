import React, { useState, useEffect, useRef, useCallback } from "react";
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  MiniMap,
  NodeTypes,
  useNodesState,
  useEdgesState,
  MarkerType,
  Position,
  NodeProps,
  Handle,
  useReactFlow,
} from "reactflow";
import "reactflow/dist/style.css";
import { motion } from "framer-motion";
import { Wrench } from "lucide-react";
import {
  NodeData,
  GraphFlow,
  FlowObject,
  NodeDefinition,
  PlanItem,
} from "./interfaces";
import { useAuth } from "@/contexts/AuthContext";
import { useStreamingData } from "../StreamingDataContext";
import axios from "../../../http/axiosAgentConfig";

// Node status enum
type NodeStatus = "IDLE" | "PROGRESS" | "DONE";

// Enhanced NodeData interface
interface EnhancedNodeData extends NodeData {
  status: NodeStatus;
}

// Custom node components with status-aware styling
const AgentNode: React.FC<NodeProps<EnhancedNodeData>> = ({
  data,
  selected,
}) => {
  // Match the hex color code inside bg-[#...]
  const bgmatcher = data.style.match(/bg-\[#([0-9A-Fa-f]{6})\]/);
  const bgcolor = bgmatcher ? bgmatcher[1] : null;

  const hasTools = data.tools && data.tools.length > 0;
  const isInProgress = data.status === "PROGRESS";
  const isDone = data.status === "DONE";

  // Dynamic styling based on status
  const getStatusStyles = () => {
    if (isInProgress) {
      return {
        containerClass: `${data.style} border-2 border-blue-500 border-opacity-80`,
        pulseEffect: true,
        borderGlow: "shadow-lg shadow-blue-500/20",
      };
    } else if (isDone) {
      return {
        containerClass: `${data.style} border-2 border-green-500 border-opacity-60`,
        pulseEffect: false,
        borderGlow: "shadow-md shadow-green-500/15",
      };
    } else {
      return {
        containerClass: data.style,
        pulseEffect: false,
        borderGlow: "shadow-md",
      };
    }
  };

  const statusStyles = getStatusStyles();

  return (
    <>
      {/* Explicit top handle using ReactFlow's Handle component */}
      <Handle
        type="target"
        position={Position.Top}
        style={{
          background: `#${bgcolor}`,
          width: 10,
          height: 10,
        }}
      />

      <motion.div
        className={`rounded-lg ${statusStyles.containerClass} ${statusStyles.borderGlow} transition-all duration-300 ${hasTools ? "min-w-[200px]" : "px-4 py-2"}`}
        initial={{ opacity: 0 }}
        animate={{
          opacity: 1,
          scale: selected ? 1.05 : 1,
          boxShadow: isInProgress
            ? [
                "0 0 0 0 rgba(96, 165, 250, 0.7)",
                "0 0 0 10px rgba(96, 165, 250, 0)",
                "0 0 0 0 rgba(96, 165, 250, 0.7)",
              ]
            : undefined,
        }}
        transition={{
          duration: 0.3,
          boxShadow: {
            repeat: isInProgress ? Infinity : 0,
            duration: 2,
            ease: "easeInOut",
          },
        }}
      >
        {/* Main node content - 75% of height when tools exist */}
        <div
          className={`${hasTools ? "px-4 py-2 border-b border-opacity-30" : "px-4 py-2"} ${hasTools ? "border-white" : ""} flex items-center relative`}
        >
          <div className="mr-2">{data.icon}</div>
          <div className="flex-1">
            <div className="font-medium text-sm flex items-center gap-2">
              {data.label}
              {isInProgress && (
                <div className="flex items-center gap-1.5 px-2 py-0.5 bg-blue-500 bg-opacity-20 rounded-full">
                  <motion.div
                    className="w-1.5 h-1.5 bg-blue-500 rounded-full"
                    animate={{ opacity: [1, 0.3, 1] }}
                    transition={{
                      duration: 1,
                      repeat: Infinity,
                      ease: "easeInOut",
                    }}
                  />
                  <span className="text-xs font-medium text-white-600">
                    Processing
                  </span>
                </div>
              )}
              {isDone && (
                <div className="flex items-center gap-1.5 px-2 py-0.5 bg-green-500 bg-opacity-20 rounded-full">
                  <div className="w-1.5 h-1.5 bg-green-500 rounded-full" />
                  <span className="text-xs font-medium text-white-600">
                    Complete
                  </span>
                </div>
              )}
            </div>
            {data.description && (
              <div
                className={`text-xs ${data.style.includes("text-white") ? "text-gray-400" : "text-white"}`}
              >
                {data.description}
              </div>
            )}
          </div>
        </div>

        {/* Tools section - 25% of height */}
        {hasTools && (
          <div className="px-4 py-2">
            <div
              className={`text-xs font-medium mb-2 ${data.style.includes("text-white") ? "text-gray-400" : "text-gray-200"} text-center border-b border-opacity-20 border-current pb-1 flex items-center justify-center gap-1`}
            >
              <Wrench className="w-3 h-3 opacity-75" />
              Tools
            </div>
            <div className="grid grid-cols-3 gap-1">
              {data.tools.map((tool, index) => (
                <div
                  key={index}
                  className={`px-2 py-1 rounded text-xs font-medium truncate text-center ${
                    data.style.includes("text-white")
                      ? "bg-white bg-opacity-20 text-white"
                      : "bg-gray-800 bg-opacity-20 text-white-200"
                  }`}
                  title={tool}
                >
                  {tool}
                </div>
              ))}
            </div>
          </div>
        )}
      </motion.div>

      {/* Explicit bottom handle using ReactFlow's Handle component */}
      <Handle
        type="source"
        position={Position.Bottom}
        style={{
          background: `#${bgcolor}`,
          width: 10,
          height: 10,
        }}
      />
    </>
  );
};

const nodeTypes: NodeTypes = {
  agent: AgentNode,
};

// Helper function to extract UID from $ref: format
const extractUidFromRef = (value: string): string => {
  if (typeof value === 'string' && value.startsWith('$ref:')) {
    return value.substring(5); // Remove '$ref:' prefix
  }
  return value;
};

// Function to generate a random icon
const getRandomIcon = (nodeType: string): React.ReactNode => {
  // Handle specific node types with consistent icons
  if (nodeType === "user_question_node") {
    return (
      <div className="w-6 h-6 rounded-full bg-white bg-opacity-30 flex items-center justify-center text-xs">
        💬
      </div>
    );
  } else if (nodeType === "final_answer_node") {
    return (
      <div className="w-6 h-6 rounded-full bg-white bg-opacity-30 flex items-center justify-center text-xs">
        🤖
      </div>
    );
  }

  // For other node types, select from a predefined set of icons
  const icons: React.ReactNode[] = [
    <div className="w-6 h-6 rounded-full bg-white bg-opacity-30 flex items-center justify-center text-xs">
      🔍
    </div>,
    <div className="w-6 h-6 rounded-full bg-white bg-opacity-30 flex items-center justify-center text-xs">
      📚
    </div>,
    <div className="w-6 h-6 rounded-full bg-white bg-opacity-30 flex items-center justify-center text-xs">
      🧠
    </div>,
    <div className="w-6 h-6 rounded-full bg-white bg-opacity-30 flex items-center justify-center text-xs">
      🔎
    </div>,
    <div className="w-6 h-6 rounded-full bg-white bg-opacity-30 flex items-center justify-center text-xs">
      🔧
    </div>,
    <div className="w-6 h-6 rounded-full bg-white bg-opacity-30 flex items-center justify-center text-xs">
      ✍️
    </div>,
  ];

  // Generate a deterministic index based on the node type
  const hash = nodeType
    .split("")
    .reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return icons[hash % icons.length];
};

// Get node style based on node type
const getNodeStyle = (nodeType: string): string => {
  if (nodeType === "user_question_node") {
    return "bg-gradient-to-r from-accent to-[#003f5c] text-white";
  } else if (nodeType === "final_answer_node") {
    return "bg-gradient-to-r from-accent to-[#003f5c] text-white";
  } else {
    return "bg-gradient-to-r from-accent to-primary text-gray-300";
  }
};

// Function to generate edge color based on source node type
const getEdgeStyle = (
  sourceNodeType: string,
): { stroke: string; color: string } => {
  if (sourceNodeType === "user_question_node") {
    return { stroke: "#003f5c", color: "#003f5c" };
  } else if (sourceNodeType === "final_answer_node") {
    return { stroke: "#003f5c", color: "#003f5c" };
  } else {
    return { stroke: "#8A2BE2", color: "#8A2BE2" };
  }
};

// Function to parse the JSON graph flow into ReactFlow nodes and edges
const parseGraphFlow = (
  graphFlow: GraphFlow,
): { nodes: Node<EnhancedNodeData>[]; edges: Edge[] } => {
  if (!graphFlow || !graphFlow.plan) {
    return { nodes: [], edges: [] };
  }

  // Create a map of node RIDs to node definitions for quick lookup
  const nodeMap: Record<string, NodeDefinition> = {};
  if (graphFlow.nodes) {
    graphFlow.nodes.forEach((node) => {
      nodeMap[extractUidFromRef(node.rid)] = node;
    });
  }

  // Create a map to store node types for edge styling
  const nodeTypeMap: Record<string, string> = {};

  // Create maps to build the layout
  const nodesByLevel: Record<number, string[]> = {}; // Level -> Node UIDs
  const nodeLevel: Record<string, number> = {}; // Node UID -> Level
  const nodePredecessors: Record<string, string[]> = {}; // Node UID -> Predecessor UIDs
  const nodeSuccessors: Record<string, string[]> = {}; // Node UID -> Successor UIDs

  // First pass: Identify predecessors and successors
  graphFlow.plan.forEach((item) => {
    const nodeId = item.uid;
    const nodeDefinition = nodeMap[item.node];
    const nodeType = nodeDefinition?.type || "custom_agent_node";
    nodeTypeMap[nodeId] = nodeType;

    if (item.after) {
      // Handle both string and array 'after' properties
      const predecessors = Array.isArray(item.after)
        ? item.after
        : [item.after];
      nodePredecessors[nodeId] = predecessors;

      // Record this node as a successor to each predecessor
      predecessors.forEach((predecessorId) => {
        if (!nodeSuccessors[predecessorId]) {
          nodeSuccessors[predecessorId] = [];
        }
        nodeSuccessors[predecessorId].push(nodeId);
      });
    } else {
      // No predecessors, this is a root node
      nodePredecessors[nodeId] = [];
      nodeLevel[nodeId] = 0;
      if (!nodesByLevel[0]) {
        nodesByLevel[0] = [];
      }
      nodesByLevel[0].push(nodeId);
    }
  });

  // Second pass: Determine node levels
  let allNodesAssigned = false;
  while (!allNodesAssigned) {
    allNodesAssigned = true;
    graphFlow.plan.forEach((item) => {
      const nodeId = item.uid;

      // Skip nodes that already have a level assigned
      if (nodeLevel[nodeId] !== undefined) {
        return;
      }

      const predecessors = nodePredecessors[nodeId] || [];

      // Check if all predecessors have levels assigned
      const allPredecessorsHaveLevels = predecessors.every(
        (predId) => nodeLevel[predId] !== undefined,
      );

      if (allPredecessorsHaveLevels) {
        // Find the maximum level among predecessors
        const maxPredLevel = Math.max(
          ...predecessors.map((predId) => nodeLevel[predId]),
        );
        const level = maxPredLevel + 1;

        // Assign this node to the next level
        nodeLevel[nodeId] = level;
        if (!nodesByLevel[level]) {
          nodesByLevel[level] = [];
        }
        nodesByLevel[level].push(nodeId);
      } else {
        allNodesAssigned = false;
      }
    });
  }

  // Create nodes with the calculated positions
  const nodes: Node<EnhancedNodeData>[] = graphFlow.plan.map((item) => {
    const nodeId = item.uid;
    const nodeDefinition = nodeMap[item.node];
    const nodeType = nodeDefinition?.type || "custom_agent_node";
    const nodeLabel =
      nodeDefinition?.name || item.meta?.display_name || "General Node";
    const nodeDescription = item.meta?.description || null;
    const nodeTools = nodeDefinition?.config?.tools || [];

    // Get level information
    const level = nodeLevel[nodeId];
    const nodesInSameLevel = nodesByLevel[level] || [];
    const indexInLevel = nodesInSameLevel.indexOf(nodeId);
    const totalInLevel = nodesInSameLevel.length;

    // Calculate position
    // Horizontal spacing increases with the number of nodes in the level
    const levelWidth = Math.max(totalInLevel * 300, 400);
    const xSpacing = levelWidth / totalInLevel;
    const xOffset = xSpacing / 2 + indexInLevel * xSpacing;
    const yOffset = level * 150;

    // Determine node style and icon
    const style = getNodeStyle(nodeType);
    const icon = getRandomIcon(nodeType);

    // Always set sourcePosition and targetPosition to ensure edges connect properly
    const sourcePosition = Position.Bottom;
    const targetPosition = Position.Top;

    return {
      id: nodeId,
      type: "agent",
      data: {
        label: nodeLabel,
        description: nodeDescription,
        style: style,
        icon: icon,
        tools: nodeTools || [],
        status: "IDLE" as NodeStatus,
      },
      position: { x: xOffset, y: yOffset },
      sourcePosition,
      targetPosition,
    };
  });

  // Create edges between nodes
  const edges: Edge[] = [];

  graphFlow.plan.forEach((item) => {
    if (item.after) {
      // Handle both string and array 'after' properties
      const predecessors = Array.isArray(item.after)
        ? item.after
        : [item.after];

      predecessors.forEach((predecessorId) => {
        const sourceNodeType =
          nodeTypeMap[predecessorId] || "custom_agent_node";
        const edgeStyle = getEdgeStyle(sourceNodeType);

        edges.push({
          id: `${predecessorId}-to-${item.uid}`,
          source: predecessorId,
          target: item.uid,
          animated: true,
          type: "default", // Simpler edge type for reliability
          style: {
            stroke: edgeStyle.stroke,
            strokeWidth: 2,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: edgeStyle.color,
            width: 10,
            height: 10,
          },
          zIndex: 1000, // Ensure edges are on top
        });
      });
    }
  });

  return { nodes, edges };
};

type ReactFlowGraphProps = {
  blueprintId?: string;
  height?: string;
  showControls?: boolean;
  showMiniMap?: boolean;
  showBackground?: boolean;
  interactive?: boolean;
  streamingDataContext?: any;
  isLiveRequest?: boolean; // Optional parameter for live tracking
};

export default function ReactFlowGraph({
  blueprintId,
  height = "400px",
  showControls = true,
  showMiniMap = true,
  showBackground = true,
  interactive = true,
  streamingDataContext = null,
  isLiveRequest = false,
}: ReactFlowGraphProps): React.ReactElement {
  const [nodes, setNodes, onNodesChange] = useNodesState<EnhancedNodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [nodeStatusMap, setNodeStatusMap] = useState<
    Record<string, NodeStatus>
  >({});

  const { fitView, zoomOut } = useReactFlow();
  const initializedRef = useRef(false);
  const streamingContext = isLiveRequest ? useStreamingData() : null;
  const prevNodeListRef = useRef<Map<string, any>>(new Map());
  const { user } = useAuth();

  // Function to update node status based on streaming data
  const updateNodeStatuses = useCallback(() => {
    if (!streamingContext) return;

    const currentNodeList = streamingContext.nodeListRef.current;
    const newStatusMap: Record<string, NodeStatus> = {};

    // Process current streaming data
    currentNodeList.forEach((nodeEntry, nodeId) => {
      if (nodeEntry.stream === "PROGRESS") {
        newStatusMap[nodeId] = "PROGRESS";
      } else if (nodeEntry.stream === "DONE") {
        newStatusMap[nodeId] = "DONE";
      } else {
        newStatusMap[nodeId] = "IDLE";
      }
    });

    // Check if there are any changes from previous state
    const hasChanges =
      JSON.stringify(newStatusMap) !== JSON.stringify(nodeStatusMap);

    if (hasChanges) {
      setNodeStatusMap(newStatusMap);

      // Update nodes with new status
      setNodes((currentNodes) =>
        currentNodes.map((node) => ({
          ...node,
          data: {
            ...node.data,
            status: newStatusMap[node.id] || "IDLE",
          },
        })),
      );
    }

    // Store current state for next comparison
    prevNodeListRef.current = new Map(currentNodeList);
  }, [streamingContext, nodeStatusMap, setNodes]);

  // Effect to monitor streaming data changes when live tracking is enabled
  useEffect(() => {
    if (!isLiveRequest || !streamingContext) return;

    // Initial status update
    updateNodeStatuses();

    // Set up interval to check for changes
    const intervalId = setInterval(() => {
      updateNodeStatuses();
    }, 100); // Check every 100ms for responsiveness

    return () => {
      clearInterval(intervalId);
    };
  }, [isLiveRequest, streamingContext, updateNodeStatuses]);

  // Reset node statuses when live tracking is disabled
  useEffect(() => {
    if (!isLiveRequest) {
      setNodes((currentNodes) =>
        currentNodes.map((node) => ({
          ...node,
          data: {
            ...node.data,
            // TODO: Due to time sync issues, some of the nodes might still hold "PROGRESS" status once reaching over here
            // status: (nodeStatusMap[node.id] == "DONE") ? nodeStatusMap[node.id] : 'IDLE' as NodeStatus
            status:
              nodeStatusMap[node.id] != "IDLE"
                ? "DONE"
                : ("IDLE" as NodeStatus),
          },
        })),
      );
      setNodeStatusMap({});
    }
  }, [isLiveRequest, setNodes]);

  // Function to convert graph flow JSON to ReactFlow format
  const convertGraphFlowToReactFlow = async (graphId: string) => {
    try {
      setIsLoading(true);
      const response = await axios.get(
        `/blueprints/available.blueprints.get?userId=${user?.username || "default"}`,
      );
      const blueprintObjects = response.data;

      // Find the specific graph flow by blueprint_id
      const targetBlueprintObj = blueprintObjects.find(
        (blueprintObj: any) =>
          blueprintObj.blueprint_id === graphId
      );

      if (targetBlueprintObj) {
        const { nodes: newNodes, edges: newEdges } =
          parseGraphFlow(targetBlueprintObj.spec_dict);

        setNodes(newNodes);
        setEdges(newEdges);

        // Auto-fit and zoom after loading
        setTimeout(() => {
          fitView({ padding: 0.2 });
          setTimeout(() => {
            zoomOut();
          }, 200);
        }, 100);
      } else {
        console.warn(`Graph flow with ID ${graphId} not found`);
      }
    } catch (error) {
      console.error("Error loading graph flow:", error);
    } finally {
      setIsLoading(false);
    }
  };

  // Load graph when blueprintId changes
  useEffect(() => {
    if (blueprintId) {
      convertGraphFlowToReactFlow(blueprintId);
    }
  }, [blueprintId]);

  // Auto-fit view when nodes/edges are loaded
  useEffect(() => {
    if (
      !initializedRef.current &&
      nodes.length > 0 &&
      edges.length > 0 &&
      !isLoading
    ) {
      initializedRef.current = true;

      setTimeout(() => {
        fitView({ padding: 0.2 });
        setTimeout(() => {
          zoomOut();
        }, 200);
      }, 100);
    }
  }, [nodes, edges, isLoading, fitView, zoomOut]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center" style={{ height }}>
        <div className="text-gray-400">Loading graph...</div>
      </div>
    );
  }

  return (
    <div className="relative" style={{ height }}>
      {/* Live Status Indicator */}
      {isLiveRequest && (
        <div className="absolute top-2 right-2 z-50 bg-black bg-opacity-70 text-white px-2 py-1 rounded text-xs flex items-center gap-2">
          <motion.div
            className="w-2 h-2 bg-green-400 rounded-full"
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
          Live Tracking
        </div>
      )}

      {/* Active Nodes Status Bar */}
      {isLiveRequest && Object.keys(nodeStatusMap).length > 0 && (
        <div className="absolute bottom-2 left-2 right-2 z-50 bg-black bg-opacity-80 text-white px-3 py-2 rounded-lg">
          <div className="flex flex-wrap gap-2 text-xs">
            {Object.entries(nodeStatusMap).map(([nodeId, status]) => {
              if (status === "IDLE") return null;

              const node = nodes.find((n) => n.id === nodeId);
              const nodeName = node?.data?.label || nodeId;

              return (
                <div
                  key={nodeId}
                  className={`flex items-center gap-1 px-2 py-1 rounded ${
                    status === "PROGRESS"
                      ? "bg-blue-500 bg-opacity-50"
                      : "bg-green-500 bg-opacity-50"
                  }`}
                >
                  <motion.div
                    className={`w-2 h-2 rounded-full ${
                      status === "PROGRESS" ? "bg-blue-400" : "bg-green-400"
                    }`}
                    animate={
                      status === "PROGRESS"
                        ? {
                            scale: [1, 1.2, 1],
                            opacity: [1, 0.7, 1],
                          }
                        : undefined
                    }
                    transition={
                      status === "PROGRESS"
                        ? {
                            duration: 1,
                            repeat: Infinity,
                          }
                        : undefined
                    }
                  />
                  <span className="truncate max-w-20">{nodeName}</span>
                  <span className="text-xs opacity-75">
                    {status === "PROGRESS" ? "Running" : "Done"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={interactive ? onNodesChange : undefined}
        onEdgesChange={interactive ? onEdgesChange : undefined}
        nodeTypes={nodeTypes}
        fitView
        elementsSelectable={interactive}
        nodesConnectable={interactive}
        nodesDraggable={interactive}
        edgesFocusable={interactive}
        defaultEdgeOptions={{
          type: "smoothstep",
          animated: true,
          style: { stroke: "#8A2BE2", strokeWidth: 3 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 20,
            height: 20,
            color: "#8A2BE2",
          },
        }}
        attributionPosition="bottom-right"
      >
        {showControls && <Controls />}
        {showMiniMap && <MiniMap />}
        {showBackground && <Background color="#aaa" gap={16} />}
      </ReactFlow>
    </div>
  );
}
