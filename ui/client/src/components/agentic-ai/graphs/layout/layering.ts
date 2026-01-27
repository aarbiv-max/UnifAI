/**
 * Layering Module
 * 
 * Responsible for:
 * - Layer assignment using longest-path algorithm
 * - Cycle breaking to handle SCCs
 * - Respecting hard constraints (entry at layer 0, exit at max layer)
 * 
 * Mental Model:
 * - Vertical (Y axis) = semantic flow: top → bottom
 * - Layer 0 = entry nodes (user_question)
 * - Layer N = exit nodes (final_answer)
 * - Middle layers = orchestration + agents + cycles
 */

import {
  NodeInfo,
  LayoutEdge,
  NodeRole,
  LayerAssignment,
  NodeConstraint,
} from "./types";
import { buildAdjacencyLists } from "./graphAnalysis";
import { ENTRY_LAYER, isPinnedTop, isPinnedBottom } from "./constraints";

// ============================================================================
// Cycle Breaking
// ============================================================================

/**
 * Identifies back-edges that should be ignored for layer assignment
 * This breaks cycles to allow topological layering
 */
export function identifyBackEdges(
  edges: LayoutEdge[],
  cycles: string[][]
): Set<string> {
  const backEdges = new Set<string>();

  cycles.forEach((cycle) => {
    if (cycle.length < 2) return;

    // For each cycle, we identify edges that go "backwards" in the cycle
    // We break the cycle by marking one edge as a back-edge
    // Strategy: mark the edge from the last node back to the first
    // This is a simple heuristic that works well for most cases
    
    // Build a set of nodes in this cycle for quick lookup
    const cycleSet = new Set(cycle);
    
    // Find edges within this cycle
    const cycleEdges: LayoutEdge[] = [];
    edges.forEach((edge) => {
      if (cycleSet.has(edge.source) && cycleSet.has(edge.target)) {
        cycleEdges.push(edge);
      }
    });

    // For a simple cycle, mark one edge as back-edge
    // Prefer to break at bidirectional edges (one direction becomes the back-edge)
    if (cycleEdges.length > 0) {
      // Find the "return" edge - typically from an agent back to orchestrator
      // Or from the last node in topological order back to an earlier node
      let backEdge = cycleEdges.find((e) => e.isBranch) || cycleEdges[0];
      backEdges.add(`${backEdge.source}::${backEdge.target}`);
    }
  });

  return backEdges;
}

// ============================================================================
// Layer Assignment
// ============================================================================

/**
 * Assigns layers to all nodes using longest-path algorithm
 * Respects constraints: entry nodes at layer 0, exit nodes at max layer
 */
export function assignLayers(
  nodes: Map<string, NodeInfo>,
  edges: LayoutEdge[],
  roles: Map<string, NodeRole>,
  constraints: NodeConstraint[],
  cycles: string[][]
): LayerAssignment {
  const nodeToLayer = new Map<string, number>();
  
  // Identify back-edges to break cycles
  const backEdges = identifyBackEdges(edges, cycles);
  
  // Build adjacency lists (excluding back-edges)
  const predecessors = new Map<string, string[]>();
  const successors = new Map<string, string[]>();
  
  nodes.forEach((_, nodeId) => {
    predecessors.set(nodeId, []);
    successors.set(nodeId, []);
  });
  
  edges.forEach((edge) => {
    const edgeKey = `${edge.source}::${edge.target}`;
    // Skip back-edges for layer assignment
    if (backEdges.has(edgeKey)) return;
    
    predecessors.get(edge.target)?.push(edge.source);
    successors.get(edge.source)?.push(edge.target);
  });

  // Step 1: Assign entry nodes to layer 0 (INVARIANT 1)
  constraints.forEach((constraint) => {
    if (isPinnedTop(constraint.nodeId, constraints)) {
      nodeToLayer.set(constraint.nodeId, ENTRY_LAYER);
    }
  });

  // If no entry nodes found, find nodes with no predecessors
  if (nodeToLayer.size === 0) {
    nodes.forEach((_, nodeId) => {
      const preds = predecessors.get(nodeId) || [];
      if (preds.length === 0 && !isPinnedBottom(nodeId, constraints)) {
        nodeToLayer.set(nodeId, ENTRY_LAYER);
      }
    });
  }

  // Step 2: Propagate layers using longest-path
  // Iterate until all nodes (except exit) have layers assigned
  const maxIterations = nodes.size * 2;
  let iterations = 0;
  let changed = true;

  while (changed && iterations < maxIterations) {
    changed = false;
    iterations++;

    nodes.forEach((_, nodeId) => {
      // Skip already assigned nodes
      if (nodeToLayer.has(nodeId)) return;
      
      // Skip exit nodes for now (they get assigned last)
      if (isPinnedBottom(nodeId, constraints)) return;

      const preds = predecessors.get(nodeId) || [];
      
      if (preds.length === 0) {
        // No predecessors (after cycle breaking) - assign to layer 1
        nodeToLayer.set(nodeId, 1);
        changed = true;
        return;
      }

      // Check if all predecessors have layers assigned
      const predLayers = preds
        .map((p) => nodeToLayer.get(p))
        .filter((l): l is number => l !== undefined);

      if (predLayers.length === preds.length) {
        // All predecessors assigned - use longest path
        const maxPredLayer = Math.max(...predLayers);
        nodeToLayer.set(nodeId, maxPredLayer + 1);
        changed = true;
      }
    });
  }

  // Step 3: Assign any remaining unassigned non-exit nodes
  // (This handles nodes in unbroken cycles)
  let currentMaxLayer = Math.max(...Array.from(nodeToLayer.values()), 0);
  
  nodes.forEach((_, nodeId) => {
    if (!nodeToLayer.has(nodeId) && !isPinnedBottom(nodeId, constraints)) {
      nodeToLayer.set(nodeId, currentMaxLayer + 1);
    }
  });

  // Recalculate max layer
  currentMaxLayer = Math.max(...Array.from(nodeToLayer.values()), 0);

  // Step 4: Assign exit nodes to max layer + 1 (INVARIANT 2)
  const exitLayer = currentMaxLayer + 1;
  constraints.forEach((constraint) => {
    if (isPinnedBottom(constraint.nodeId, constraints)) {
      nodeToLayer.set(constraint.nodeId, exitLayer);
    }
  });

  // Build layer-to-nodes mapping
  const layerToNodes = new Map<number, string[]>();
  nodeToLayer.forEach((layer, nodeId) => {
    if (!layerToNodes.has(layer)) {
      layerToNodes.set(layer, []);
    }
    layerToNodes.get(layer)!.push(nodeId);
  });

  // Calculate min and max layers
  const layers = Array.from(nodeToLayer.values());
  const minLayer = Math.min(...layers);
  const maxLayer = Math.max(...layers);

  return {
    nodeToLayer,
    layerToNodes,
    minLayer,
    maxLayer,
  };
}

// ============================================================================
// Layer Compaction
// ============================================================================

/**
 * Compacts layers to remove gaps
 * Maintains constraint invariants
 */
export function compactLayers(
  layerAssignment: LayerAssignment,
  constraints: NodeConstraint[]
): LayerAssignment {
  const { nodeToLayer, layerToNodes, minLayer, maxLayer } = layerAssignment;
  
  // Get sorted unique layer values
  const usedLayers = Array.from(new Set(nodeToLayer.values())).sort((a, b) => a - b);
  
  // Create mapping from old layer to new layer
  const layerMapping = new Map<number, number>();
  usedLayers.forEach((oldLayer, index) => {
    layerMapping.set(oldLayer, index);
  });

  // Create new assignments
  const newNodeToLayer = new Map<string, number>();
  const newLayerToNodes = new Map<number, string[]>();

  nodeToLayer.forEach((oldLayer, nodeId) => {
    const newLayer = layerMapping.get(oldLayer) || 0;
    newNodeToLayer.set(nodeId, newLayer);
    
    if (!newLayerToNodes.has(newLayer)) {
      newLayerToNodes.set(newLayer, []);
    }
    newLayerToNodes.get(newLayer)!.push(nodeId);
  });

  const newLayers = Array.from(newNodeToLayer.values());
  
  return {
    nodeToLayer: newNodeToLayer,
    layerToNodes: newLayerToNodes,
    minLayer: Math.min(...newLayers),
    maxLayer: Math.max(...newLayers),
  };
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Gets the layer span of an edge (how many layers it crosses)
 */
export function getEdgeSpan(
  edge: LayoutEdge,
  nodeToLayer: Map<string, number>
): number {
  const sourceLayer = nodeToLayer.get(edge.source);
  const targetLayer = nodeToLayer.get(edge.target);
  
  if (sourceLayer === undefined || targetLayer === undefined) {
    return 0;
  }
  
  return Math.abs(targetLayer - sourceLayer);
}

/**
 * Checks if an edge spans multiple layers (long edge)
 */
export function isLongEdge(
  edge: LayoutEdge,
  nodeToLayer: Map<string, number>
): boolean {
  return getEdgeSpan(edge, nodeToLayer) > 1;
}

/**
 * Gets all long edges that need dummy nodes for proper routing
 */
export function getLongEdges(
  edges: LayoutEdge[],
  nodeToLayer: Map<string, number>
): LayoutEdge[] {
  return edges.filter((edge) => isLongEdge(edge, nodeToLayer));
}
