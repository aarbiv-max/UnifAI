/**
 * Shared Type Definitions for Graph Layout
 * 
 * This module contains all type definitions used across the layout system.
 */

import { PlanItem, NodeDefinition } from "../interfaces";

// ============================================================================
// Node Role Types
// ============================================================================

/**
 * Semantic role of a node in the graph
 * - entry: User input node (must be at top)
 * - exit: Final answer node (must be at bottom)
 * - orchestrator: Central hub/controller node
 * - agent: Processing nodes (custom agents)
 * - control: Control-flow nodes (routers, conditions)
 */
export type NodeRole = "entry" | "exit" | "orchestrator" | "agent" | "control";

// ============================================================================
// Depth Group Types (Relative Position to Orchestrator)
// ============================================================================

/**
 * Semantic depth group of a node relative to the orchestrator/hub
 * 
 * This classifies nodes based on their directed relationship to the orchestrator:
 * - UPSTREAM: Can reach orchestrator but orchestrator cannot reach this node
 * - DOWNSTREAM: Orchestrator can reach this node but this node cannot reach orchestrator
 * - CYCLIC: Both directions exist (bidirectional relationship with orchestrator)
 * - ISOLATED: Neither direction exists (no path to/from orchestrator)
 * - HUB: The orchestrator/hub node itself
 * - PINNED_TOP: Entry nodes (special handling, always at top)
 * - PINNED_BOTTOM: Exit nodes (special handling, always at bottom)
 */
export type DepthGroup = 
  | "UPSTREAM" 
  | "DOWNSTREAM" 
  | "CYCLIC" 
  | "ISOLATED" 
  | "HUB"
  | "PINNED_TOP"
  | "PINNED_BOTTOM";

/**
 * Depth analysis result for a single node
 */
export interface NodeDepthInfo {
  /** The node ID */
  nodeId: string;
  /** Depth group classification */
  depthGroup: DepthGroup;
  /** Shortest directed distance TO the orchestrator (-1 if unreachable) */
  distanceToOrchestrator: number;
  /** Shortest directed distance FROM the orchestrator (-1 if unreachable) */
  distanceFromOrchestrator: number;
  /** Combined semantic depth (used for fine-grained ordering within groups) */
  semanticDepth: number;
}

/**
 * Complete depth analysis for the graph
 */
export interface DepthAnalysis {
  /** Map of node ID to depth info */
  nodeDepths: Map<string, NodeDepthInfo>;
  /** Nodes grouped by their depth group */
  groupedNodes: Map<DepthGroup, string[]>;
  /** The orchestrator/hub node ID(s) used for analysis */
  hubNodes: string[];
  /** Whether the graph has multiple hubs */
  isMultiHub: boolean;
}

// ============================================================================
// Graph Structure Types
// ============================================================================

/**
 * Represents an edge in the graph
 */
export interface LayoutEdge {
  source: string;
  target: string;
  isBidirectional: boolean;
  isBranch: boolean;
}

// ============================================================================
// Node Type Classification
// ============================================================================

/**
 * Known node types in the system.
 * Using a union type prevents typos and makes the code more self-documenting.
 */
export type NodeType =
  | "user_question_node"
  | "final_answer_node"
  | "orchestrator_node"
  | "router_direct"
  | "router"
  | "condition"
  | "custom_agent_node";

/**
 * Basic node information
 */
export interface NodeInfo {
  type: NodeType | string; // Allow string for unknown/future types
  label: string;
}

/**
 * Complete graph structure after analysis
 */
export interface GraphStructure {
  nodes: Map<string, NodeInfo>;
  edges: LayoutEdge[];
  bidirectionalPairs: Set<string>;
  cycles: string[][];
  roles: Map<string, NodeRole>;
  /** Detected star/hub-and-spoke patterns */
  starGroups: StarGroup[];
  /** Depth analysis relative to orchestrator/hub nodes */
  depthAnalysis: DepthAnalysis;
}

// ============================================================================
// Star / Hub-and-Spoke Types
// ============================================================================

/**
 * Represents a star (hub-and-spoke) pattern in the graph
 * 
 * A star is detected when:
 * - A hub node has ≥3 bidirectional neighbors (spokes)
 * - All spokes are in the semantic middle band (not entry/exit)
 * - No strong ordering constraints between spokes
 * 
 * Star patterns require special layout treatment:
 * - Spokes are distributed radially around the hub
 * - Symmetry is preserved (barycenter doesn't collapse siblings)
 * - Edge lengths are kept roughly equal
 */
export interface StarGroup {
  /** Unique identifier for this star group */
  id: string;
  /** The central hub node (usually orchestrator) */
  hubId: string;
  /** Spoke nodes connected bidirectionally to the hub */
  spokeIds: string[];
  /** Number of spokes */
  spokeCount: number;
}

/**
 * Spoke placement in a star layout
 */
export interface SpokePlacement {
  nodeId: string;
  /** Quadrant: 0=upper-left, 1=upper-right, 2=lower-left, 3=lower-right */
  quadrant: number;
  /** Horizontal offset from hub center */
  offsetX: number;
  /** Vertical offset from hub center */
  offsetY: number;
}

// ============================================================================
// Constraint Types
// ============================================================================

/**
 * Constraint type for pinned nodes
 */
export type ConstraintType = "pin_top" | "pin_bottom" | "none";

/**
 * Node constraint definition
 */
export interface NodeConstraint {
  nodeId: string;
  type: ConstraintType;
  priority: number; // Higher priority = stronger constraint
}

/**
 * Boundary constraints for the layout
 */
export interface LayoutBounds {
  minY: number;
  maxY: number;
  reservedTop: Set<string>;    // Node IDs that must be at top
  reservedBottom: Set<string>; // Node IDs that must be at bottom
}

// ============================================================================
// Layer Types
// ============================================================================

/**
 * Result of layer assignment
 */
export interface LayerAssignment {
  nodeToLayer: Map<string, number>;
  layerToNodes: Map<number, string[]>;
  minLayer: number;
  maxLayer: number;
}

// ============================================================================
// Ordering Types
// ============================================================================

/**
 * Result of ordering optimization
 */
export interface OrderingResult {
  orderedLayers: Map<number, string[]>;
  crossingCount: number;
}

// ============================================================================
// Position Types
// ============================================================================

/**
 * 2D position
 */
export interface Position {
  x: number;
  y: number;
}

/**
 * Final layout result
 */
export interface LayoutResult {
  positions: Map<string, Position>;
  layers: Map<number, string[]>;
  cycleGroups: Map<string, string[]>;
  starGroups: StarGroup[];
  depthAnalysis: DepthAnalysis;
  metadata: LayoutMetadata;
}

/**
 * Layout metadata for debugging and analysis
 */
export interface LayoutMetadata {
  entryNodes: string[];
  exitNodes: string[];
  orchestratorNodes: string[];
  cycleCount: number;
  crossingCount: number;
  starGroupCount: number;
  /** Count of nodes in each depth group */
  depthGroupCounts: Record<DepthGroup, number>;
}

// ============================================================================
// Configuration Types
// ============================================================================

/**
 * Layout configuration options
 */
export interface LayoutConfig {
  /** Vertical spacing between layers (Y axis = semantic flow) */
  layerSpacing: number;
  /** Horizontal spacing between nodes in same layer (X axis = structural spread) */
  nodeSpacing: number;
  /** Grid snap size */
  gridSize: number;
  /** Whether to center orchestrator nodes */
  orchestratorCentric: boolean;
  /** Cycle visualization style */
  cycleVisualization: "vertical" | "ushape" | "auto";
  /** 
   * Whether to compute depth analysis for semantic grouping.
   * Depth analysis provides better layout for orchestrator-centric graphs
   * but adds computational overhead. Set to false for simple graphs or
   * when performance is critical.
   * @default true
   */
  enableDepthAnalysis: boolean;
}

/**
 * Default layout configuration
 */
export const DEFAULT_LAYOUT_CONFIG: LayoutConfig = {
  layerSpacing: 200,
  nodeSpacing: 300,
  gridSize: 16,
  orchestratorCentric: true,
  cycleVisualization: "auto",
  enableDepthAnalysis: true,
};

// ============================================================================
// Input Types (from interfaces.tsx)
// ============================================================================

export type { PlanItem, NodeDefinition };
