/**
 * Ordering Module
 * 
 * Responsible for:
 * - Crossing minimization using barycenter heuristic
 * - Layer sweeping (forward and backward passes)
 * - Node ordering within layers
 * 
 * Note: Ordering optimizations are SECONDARY to constraint invariants.
 * Entry/exit nodes must maintain their positions even if it increases crossings.
 */

import {
  LayoutEdge,
  NodeRole,
  NodeConstraint,
  LayerAssignment,
  OrderingResult,
} from "./types";
import { isPinnedTop, isPinnedBottom } from "./constraints";

// ============================================================================
// Adjacency Building
// ============================================================================

/**
 * Builds adjacency lists for ordering calculations
 */
function buildOrderingAdjacency(
  edges: LayoutEdge[],
  nodeToLayer: Map<string, number>
): { incoming: Map<string, string[]>; outgoing: Map<string, string[]> } {
  const incoming = new Map<string, string[]>();
  const outgoing = new Map<string, string[]>();

  // Initialize
  nodeToLayer.forEach((_, nodeId) => {
    incoming.set(nodeId, []);
    outgoing.set(nodeId, []);
  });

  // Only include edges between adjacent layers for ordering
  edges.forEach((edge) => {
    const sourceLayer = nodeToLayer.get(edge.source);
    const targetLayer = nodeToLayer.get(edge.target);
    
    if (sourceLayer === undefined || targetLayer === undefined) return;
    
    // Include all edges for ordering (including long edges and back-edges)
    outgoing.get(edge.source)?.push(edge.target);
    incoming.get(edge.target)?.push(edge.source);
  });

  return { incoming, outgoing };
}

// ============================================================================
// Barycenter Calculation
// ============================================================================

/**
 * Calculates the barycenter (weighted average position) of a node
 * based on its neighbors in an adjacent layer
 */
function calculateBarycenter(
  nodeId: string,
  neighbors: string[],
  neighborPositions: Map<string, number>
): number {
  if (neighbors.length === 0) {
    return Infinity; // No neighbors = push to end
  }

  const positions = neighbors
    .map((n) => neighborPositions.get(n))
    .filter((p): p is number => p !== undefined);

  if (positions.length === 0) {
    return Infinity;
  }

  // Return median instead of mean for more stable ordering
  const sorted = [...positions].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  
  if (sorted.length % 2 === 0) {
    return (sorted[mid - 1] + sorted[mid]) / 2;
  }
  return sorted[mid];
}

// ============================================================================
// Layer Sorting
// ============================================================================

/**
 * Sorts nodes within a layer based on barycenter values
 * Respects constraints: pinned nodes maintain relative priority
 */
function sortLayerByBarycenter(
  layer: number,
  layerNodes: string[],
  neighborMap: Map<string, string[]>,
  neighborPositions: Map<string, number>,
  roles: Map<string, NodeRole>,
  constraints: NodeConstraint[]
): string[] {
  if (layerNodes.length <= 1) {
    return layerNodes;
  }

  // Calculate barycenter for each node
  const nodeScores = layerNodes.map((nodeId, originalIndex) => {
    const neighbors = neighborMap.get(nodeId) || [];
    const barycenter = calculateBarycenter(nodeId, neighbors, neighborPositions);
    const role = roles.get(nodeId);
    
    // Priority: entry nodes first, exit nodes last, others by role
    let priority = 0;
    if (isPinnedTop(nodeId, constraints)) {
      priority = -1000; // Always first
    } else if (isPinnedBottom(nodeId, constraints)) {
      priority = 1000; // Always last
    } else if (role === "orchestrator") {
      priority = 0; // Center
    }

    return {
      nodeId,
      barycenter,
      originalIndex,
      priority,
      hasNeighbors: neighbors.length > 0,
    };
  });

  // Sort by priority first, then barycenter, then original index
  nodeScores.sort((a, b) => {
    // Priority takes precedence
    if (a.priority !== b.priority) {
      return a.priority - b.priority;
    }

    // Nodes with neighbors come before nodes without
    if (a.hasNeighbors !== b.hasNeighbors) {
      return a.hasNeighbors ? -1 : 1;
    }

    // Sort by barycenter
    if (a.barycenter !== b.barycenter) {
      if (a.barycenter === Infinity) return 1;
      if (b.barycenter === Infinity) return -1;
      return a.barycenter - b.barycenter;
    }

    // Stable sort by original index
    return a.originalIndex - b.originalIndex;
  });

  return nodeScores.map((s) => s.nodeId);
}

// ============================================================================
// Crossing Counting
// ============================================================================

/**
 * Counts edge crossings between two adjacent layers
 */
function countLayerCrossings(
  upperLayer: string[],
  lowerLayer: string[],
  edges: LayoutEdge[],
  nodeToLayer: Map<string, number>
): number {
  // Build position maps
  const upperPos = new Map(upperLayer.map((n, i) => [n, i]));
  const lowerPos = new Map(lowerLayer.map((n, i) => [n, i]));

  // Get layer numbers
  let upperLayerNum = -Infinity;
  let lowerLayerNum = Infinity;
  upperLayer.forEach((n) => {
    const layer = nodeToLayer.get(n);
    if (layer !== undefined) upperLayerNum = Math.max(upperLayerNum, layer);
  });
  lowerLayer.forEach((n) => {
    const layer = nodeToLayer.get(n);
    if (layer !== undefined) lowerLayerNum = Math.min(lowerLayerNum, layer);
  });

  // Collect edge pairs between these layers
  const edgePairs: [number, number][] = [];
  
  edges.forEach((edge) => {
    const sourceLayer = nodeToLayer.get(edge.source);
    const targetLayer = nodeToLayer.get(edge.target);
    
    if (sourceLayer === undefined || targetLayer === undefined) return;

    // Check if edge connects these two layers
    const sourceInUpper = upperPos.has(edge.source);
    const targetInLower = lowerPos.has(edge.target);
    const sourceInLower = lowerPos.has(edge.source);
    const targetInUpper = upperPos.has(edge.target);

    if (sourceInUpper && targetInLower) {
      const uIdx = upperPos.get(edge.source)!;
      const lIdx = lowerPos.get(edge.target)!;
      edgePairs.push([uIdx, lIdx]);
    } else if (sourceInLower && targetInUpper) {
      // Reverse edge
      const uIdx = upperPos.get(edge.target)!;
      const lIdx = lowerPos.get(edge.source)!;
      edgePairs.push([uIdx, lIdx]);
    }
  });

  // Count crossings using inversion count
  let crossings = 0;
  for (let i = 0; i < edgePairs.length; i++) {
    for (let j = i + 1; j < edgePairs.length; j++) {
      const [u1, l1] = edgePairs[i];
      const [u2, l2] = edgePairs[j];
      // Crossing occurs when edges cross
      if ((u1 - u2) * (l1 - l2) < 0) {
        crossings++;
      }
    }
  }

  return crossings;
}

/**
 * Counts total crossings in the entire graph
 */
function countTotalCrossings(
  orderedLayers: Map<number, string[]>,
  edges: LayoutEdge[],
  nodeToLayer: Map<string, number>
): number {
  const layers = Array.from(orderedLayers.keys()).sort((a, b) => a - b);
  let total = 0;

  for (let i = 0; i < layers.length - 1; i++) {
    const upperLayer = orderedLayers.get(layers[i]) || [];
    const lowerLayer = orderedLayers.get(layers[i + 1]) || [];
    total += countLayerCrossings(upperLayer, lowerLayer, edges, nodeToLayer);
  }

  return total;
}

// ============================================================================
// Main Ordering Algorithm
// ============================================================================

/**
 * Minimizes edge crossings using iterative barycenter sweeping
 * Returns optimized node ordering within each layer
 */
export function minimizeCrossings(
  layerAssignment: LayerAssignment,
  edges: LayoutEdge[],
  roles: Map<string, NodeRole>,
  constraints: NodeConstraint[],
  maxIterations: number = 8
): OrderingResult {
  const { nodeToLayer, layerToNodes } = layerAssignment;
  
  // Create mutable copy of layer ordering
  const orderedLayers = new Map<number, string[]>();
  layerToNodes.forEach((nodes, layer) => {
    orderedLayers.set(layer, [...nodes]);
  });

  // Get sorted layer numbers
  const layers = Array.from(orderedLayers.keys()).sort((a, b) => a - b);
  
  if (layers.length === 0) {
    return { orderedLayers, crossingCount: 0 };
  }

  // Build adjacency for barycenter calculation
  const { incoming, outgoing } = buildOrderingAdjacency(edges, nodeToLayer);

  // Track best ordering
  let bestOrdering = new Map<number, string[]>();
  orderedLayers.forEach((nodes, layer) => {
    bestOrdering.set(layer, [...nodes]);
  });
  let bestCrossings = countTotalCrossings(orderedLayers, edges, nodeToLayer);

  // Iterative sweeping
  for (let iter = 0; iter < maxIterations; iter++) {
    let improved = false;

    // Forward sweep (top to bottom)
    for (let i = 1; i < layers.length; i++) {
      const currentLayer = layers[i];
      const prevLayer = layers[i - 1];
      const currentNodes = orderedLayers.get(currentLayer) || [];
      const prevNodes = orderedLayers.get(prevLayer) || [];
      
      // Build position map for previous layer
      const prevPositions = new Map(prevNodes.map((n, idx) => [n, idx]));
      
      // Sort current layer
      const sorted = sortLayerByBarycenter(
        currentLayer,
        currentNodes,
        incoming,
        prevPositions,
        roles,
        constraints
      );
      
      orderedLayers.set(currentLayer, sorted);
    }

    // Check for improvement
    let crossings = countTotalCrossings(orderedLayers, edges, nodeToLayer);
    if (crossings < bestCrossings) {
      bestCrossings = crossings;
      improved = true;
      orderedLayers.forEach((nodes, layer) => {
        bestOrdering.set(layer, [...nodes]);
      });
    }

    // Backward sweep (bottom to top)
    for (let i = layers.length - 2; i >= 0; i--) {
      const currentLayer = layers[i];
      const nextLayer = layers[i + 1];
      const currentNodes = orderedLayers.get(currentLayer) || [];
      const nextNodes = orderedLayers.get(nextLayer) || [];
      
      // Build position map for next layer
      const nextPositions = new Map(nextNodes.map((n, idx) => [n, idx]));
      
      // Sort current layer
      const sorted = sortLayerByBarycenter(
        currentLayer,
        currentNodes,
        outgoing,
        nextPositions,
        roles,
        constraints
      );
      
      orderedLayers.set(currentLayer, sorted);
    }

    // Check for improvement
    crossings = countTotalCrossings(orderedLayers, edges, nodeToLayer);
    if (crossings < bestCrossings) {
      bestCrossings = crossings;
      improved = true;
      orderedLayers.forEach((nodes, layer) => {
        bestOrdering.set(layer, [...nodes]);
      });
    }

    // Stop if no improvement
    if (!improved) {
      break;
    }
  }

  return {
    orderedLayers: bestOrdering,
    crossingCount: bestCrossings,
  };
}

// ============================================================================
// Orchestrator Centering
// ============================================================================

/**
 * Adjusts ordering to center orchestrator nodes within their layers
 * This is applied after crossing minimization as a refinement
 */
export function centerOrchestrators(
  orderedLayers: Map<number, string[]>,
  roles: Map<string, NodeRole>,
  constraints: NodeConstraint[]
): Map<number, string[]> {
  const result = new Map<number, string[]>();

  orderedLayers.forEach((nodes, layer) => {
    if (nodes.length <= 1) {
      result.set(layer, [...nodes]);
      return;
    }

    // Find orchestrator nodes in this layer
    const orchestrators: string[] = [];
    const others: string[] = [];
    
    nodes.forEach((nodeId) => {
      if (roles.get(nodeId) === "orchestrator") {
        orchestrators.push(nodeId);
      } else {
        others.push(nodeId);
      }
    });

    if (orchestrators.length === 0) {
      result.set(layer, [...nodes]);
      return;
    }

    // Place orchestrators in the center
    const midpoint = Math.floor(others.length / 2);
    const reordered = [
      ...others.slice(0, midpoint),
      ...orchestrators,
      ...others.slice(midpoint),
    ];

    result.set(layer, reordered);
  });

  return result;
}
