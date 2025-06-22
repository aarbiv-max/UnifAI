import React, { useState, useEffect, useRef } from 'react';
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
  useReactFlow 
} from 'reactflow';
import 'reactflow/dist/style.css';
import { motion } from 'framer-motion';
import { Wrench } from 'lucide-react';
import { NodeData, GraphFlow, FlowObject } from './interfaces';
import axios from '../../../http/axiosAgentConfig'

// Custom node components
const AgentNode: React.FC<NodeProps<NodeData>> = ({ data, selected }) => {
  // Match the hex color code inside bg-[#...]
  const bgmatcher = data.style.match(/bg-\[#([0-9A-Fa-f]{6})\]/);
  const bgcolor = bgmatcher ? bgmatcher[1] : null;
  
  const hasTools = data.tools && data.tools.length > 0;

  return (
    <>
      {/* Explicit top handle using ReactFlow's Handle component */}
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: `#${bgcolor}`, width: 10, height: 10 }}
      />
      
      <motion.div 
        className={`rounded-lg shadow-md ${data.style} transition-all ${hasTools ? 'min-w-[200px]' : 'px-4 py-2'}`}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1, scale: selected ? 1.05 : 1 }}
        transition={{ duration: 0.3 }}
      >
        {/* Main node content - 75% of height when tools exist */}
        <div className={`${hasTools ? 'px-4 py-2 border-b border-opacity-30' : 'px-4 py-2'} ${hasTools ? 'border-white' : ''} flex items-center`}>
          <div className="mr-2">
            {data.icon}
          </div>
          <div className="flex-1">
            <div className="font-medium text-sm">{data.label}</div>
            {data.description && (
              <div className={`text-xs ${data.style.includes("text-white") ? "text-gray-400" : "text-white"}`}>
                {data.description}
              </div>
            )}
          </div>
        </div>
        
        {/* Tools section - 25% of height */}
        {hasTools && (
          <div className="px-4 py-2">
            <div className={`text-xs font-medium mb-2 ${data.style.includes("text-white") ? "text-gray-400" : "text-gray-200"} text-center border-b border-opacity-20 border-current pb-1 flex items-center justify-center gap-1`}>
              <Wrench className="w-3 h-3 opacity-75" />
              Tools
            </div>
            <div className="flex flex-wrap gap-1">
              {data.tools.map((tool, index) => (
                <div
                  key={index}
                  className={`px-2 py-1 rounded text-xs font-medium ${
                    data.style.includes("text-white") 
                      ? "bg-white bg-opacity-20 text-white" 
                      : "bg-gray-800 bg-opacity-20 text-gray-800"
                  }`}
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
        style={{ background: `#${bgcolor}`, width: 10, height: 10 }}
      />
    </>
  );
};

const nodeTypes: NodeTypes = {
  agent: AgentNode,
};

// Function to generate a random icon
const getRandomIcon = (nodeType: string): React.ReactNode => {
  // Handle specific node types with consistent icons
  if (nodeType === 'user_question_node') {
    return <div className="w-6 h-6 rounded-full bg-white bg-opacity-30 flex items-center justify-center text-xs">💬</div>;
  } else if (nodeType === 'final_answer_node') {
    return <div className="w-6 h-6 rounded-full bg-white bg-opacity-30 flex items-center justify-center text-xs">🤖</div>;
  }
  
  // For other node types, select from a predefined set of icons
  const icons: React.ReactNode[] = [
    <div className="w-6 h-6 rounded-full bg-white bg-opacity-30 flex items-center justify-center text-xs">🔍</div>,
    <div className="w-6 h-6 rounded-full bg-white bg-opacity-30 flex items-center justify-center text-xs">📚</div>,
    <div className="w-6 h-6 rounded-full bg-white bg-opacity-30 flex items-center justify-center text-xs">🧠</div>,
    <div className="w-6 h-6 rounded-full bg-white bg-opacity-30 flex items-center justify-center text-xs">🔎</div>,
    <div className="w-6 h-6 rounded-full bg-white bg-opacity-30 flex items-center justify-center text-xs">🔧</div>,
    <div className="w-6 h-6 rounded-full bg-white bg-opacity-30 flex items-center justify-center text-xs">✍️</div>,
  ];
  
  // Generate a deterministic index based on the node type
  const hash = nodeType.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return icons[hash % icons.length];
};

// Get node style based on node type
const getNodeStyle = (nodeType: string): string => {
  if (nodeType === 'user_question_node') {
    return 'bg-[#003f5c] text-white';
  } else if (nodeType === 'final_answer_node') {
    return 'bg-[#ffa600] text-white';
  } else {
    return 'bg-[#7E4794] text-gray-800';
  }
};

// Function to generate edge color based on source node type
const getEdgeStyle = (sourceNodeType: string): { stroke: string; color: string } => {
  if (sourceNodeType === 'user_question_node') {
    return { stroke: '#003f5c', color: '#003f5c' };
  } else if (sourceNodeType === 'final_answer_node') {
    return { stroke: '#ffa600', color: '#ffa600' };
  } else {
    return { stroke: '#7E4794', color: '#7E4794' };
  }
};

// Function to parse the JSON graph flow into ReactFlow nodes and edges
const parseGraphFlow = (graphFlow: GraphFlow): { nodes: Node<NodeData>[]; edges: Edge[] } => {
  if (!graphFlow || !graphFlow.plan) {
    return { nodes: [], edges: [] };
  }

  // Create a map to store node types for edge styling
  const nodeTypeMap: Record<string, string> = {};
  
  // Create maps to build the layout
  const nodesByLevel: Record<number, string[]> = {}; // Level -> Node IDs
  const nodeLevel: Record<string, number> = {}; // Node ID -> Level
  const nodePredecessors: Record<string, string[]> = {}; // Node ID -> Predecessor IDs
  const nodeSuccessors: Record<string, string[]> = {}; // Node ID -> Successor IDs
  
  // First pass: Identify predecessors and successors
  graphFlow.plan.forEach(item => {
    const nodeId = item.uid;
    const nodeType = item.node?.type || 'custom_agent_node';
    nodeTypeMap[nodeId] = nodeType;
    
    if (item.after) {
      // Handle both string and array 'after' properties
      const predecessors = Array.isArray(item.after) ? item.after : [item.after];
      nodePredecessors[nodeId] = predecessors;
      
      // Record this node as a successor to each predecessor
      predecessors.forEach(predecessorId => {
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
    graphFlow.plan.forEach(item => {
      const nodeId = item.uid;
      
      // Skip nodes that already have a level assigned
      if (nodeLevel[nodeId] !== undefined) {
        return;
      }
      
      const predecessors = nodePredecessors[nodeId] || [];
      
      // Check if all predecessors have levels assigned
      const allPredecessorsHaveLevels = predecessors.every(predId => 
        nodeLevel[predId] !== undefined
      );
      
      if (allPredecessorsHaveLevels) {
        // Find the maximum level among predecessors
        const maxPredLevel = Math.max(...predecessors.map(predId => nodeLevel[predId]));
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
  const nodes: Node<NodeData>[] = graphFlow.plan.map(item => {
    const nodeId = item.uid;
    const nodeType = item.node?.type || 'custom_agent_node';
    const nodeLabel = item.meta?.display_name || item.node?._meta.display_name || "General Node";
    const nodeDescription = item.meta?.description || item.node?._meta.description || null;
    const nodeTools = item.node?.tools || [];
    
    // Get level information
    const level = nodeLevel[nodeId];
    const nodesInSameLevel = nodesByLevel[level] || [];
    const indexInLevel = nodesInSameLevel.indexOf(nodeId);
    const totalInLevel = nodesInSameLevel.length;
    
    // Calculate position
    // Horizontal spacing increases with the number of nodes in the level
    const levelWidth = Math.max(totalInLevel * 300, 400);
    const xSpacing = levelWidth / totalInLevel;
    const xOffset = (xSpacing / 2) + (indexInLevel * xSpacing);
    const yOffset = level * 150;
    
    // Determine node style and icon
    const style = getNodeStyle(nodeType);
    const icon = getRandomIcon(nodeType);
    
    // Always set sourcePosition and targetPosition to ensure edges connect properly
    const sourcePosition = Position.Bottom;
    const targetPosition = Position.Top;
    
    return {
      id: nodeId,
      type: 'agent',
      data: {
        label: nodeLabel,
        description: nodeDescription,
        style: style,
        icon: icon,
        tools: nodeTools
      },
      position: { x: xOffset, y: yOffset },
      sourcePosition,
      targetPosition
    };
  });
  
  // Create edges between nodes
  const edges: Edge[] = [];
  
  graphFlow.plan.forEach(item => {
    if (item.after) {
      // Handle both string and array 'after' properties
      const predecessors = Array.isArray(item.after) ? item.after : [item.after];
      
      predecessors.forEach(predecessorId => {
        const sourceNodeType = nodeTypeMap[predecessorId] || 'custom_agent_node';
        const edgeStyle = getEdgeStyle(sourceNodeType);
        
        edges.push({
          id: `${predecessorId}-to-${item.uid}`,
          source: predecessorId,
          target: item.uid,
          animated: true,
          type: 'default', // Simpler edge type for reliability
          style: { 
            stroke: edgeStyle.stroke, 
            strokeWidth: 2
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: edgeStyle.color,
            width: 10,
            height: 10
          },
          zIndex: 1000 // Ensure edges are on top
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
};

export default function ReactFlowGraph({
  blueprintId,
  height = "400px",
  showControls = true,
  showMiniMap = true,
  showBackground = true,
  interactive = true
}: ReactFlowGraphProps): React.ReactElement {
  const [nodes, setNodes, onNodesChange] = useNodesState<NodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [isLoading, setIsLoading] = useState(false);

  const { fitView, zoomOut } = useReactFlow();
  const initializedRef = useRef(false);

  // Function to convert graph flow JSON to ReactFlow format
  const convertGraphFlowToReactFlow = async (graphId: string) => {
    try {
      setIsLoading(true);
      const response = await axios.get('/api/blueprints/available.blueprints.get');
      const plans = response.data.flatMap((plan) => plan);
      
      // Find the specific graph flow by ID
      const targetGraphFlow = plans.find(plan => 
        Object.keys(plan).includes(graphId)
      );
      
      if (targetGraphFlow && targetGraphFlow[graphId]) {
        const graphFlow = targetGraphFlow[graphId] as GraphFlow;
        const { nodes: newNodes, edges: newEdges } = parseGraphFlow(graphFlow);
        
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
      console.error('Error loading graph flow:', error);
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
    if (!initializedRef.current && nodes.length > 0 && edges.length > 0 && !isLoading) {
      initializedRef.current = true;
      
      setTimeout(() => {
        fitView({ padding: 0.2 });
        setTimeout(() => {
          zoomOut();
        }, 200);
      }, 100);
    }
  }, [nodes, edges, isLoading]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center" style={{ height }}>
        <div className="text-gray-400">Loading graph...</div>
      </div>
    );
  }

  return (
    <div style={{ height }}>
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
        connectionLineType="smoothstep"
        defaultEdgeOptions={{
          type: 'smoothstep',
          animated: true,
          style: { stroke: '#003f5c', strokeWidth: 3 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 20,
            height: 20,
            color: '#003f5c'
          }
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