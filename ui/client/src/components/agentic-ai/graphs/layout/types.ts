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

/**
 * Basic node information
 */
export interface NodeInfo {
  type: string;
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
};

// ============================================================================
// Input Types (from interfaces.tsx)
// ============================================================================

export type { PlanItem, NodeDefinition };
