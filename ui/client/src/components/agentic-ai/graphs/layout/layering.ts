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
  DepthAnalysis,
  DepthGroup,
} from "./types";
import { buildAdjacencyLists } from "./graphAnalysis";
import { 
  ENTRY_LAYER, 
  isPinnedTop, 
  isPinnedBottom,
  DEPTH_GROUP_BANDS,
  computeIdealLayer,
} from "./constraints";

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

// ============================================================================
// Depth-Aware Layer Assignment
// ============================================================================

/**
 * Assigns layers using depth analysis to ensure proper vertical stratification
 * 
 * This function improves upon the basic longest-path algorithm by:
 * 1. Using depth groups to determine relative layer positions
 * 2. Ensuring UPSTREAM nodes are always above the hub layer
 * 3. Ensuring DOWNSTREAM nodes are always below the hub layer
 * 4. Keeping CYCLIC nodes at or near the hub layer
 * 
 * @param nodes - Map of node IDs to node info
 * @param edges - All edges in the graph
 * @param roles - Map of node IDs to semantic roles
 * @param constraints - Layout constraints
 * @param cycles - Detected cycles
 * @param depthAnalysis - Depth analysis results
 * @returns Layer assignment with depth-aware stratification
 */
export function assignLayersWithDepth(
  nodes: Map<string, NodeInfo>,
  edges: LayoutEdge[],
  roles: Map<string, NodeRole>,
  constraints: NodeConstraint[],
  cycles: string[][],
  depthAnalysis: DepthAnalysis
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
    if (backEdges.has(edgeKey)) return;
    
    predecessors.get(edge.target)?.push(edge.source);
    successors.get(edge.source)?.push(edge.target);
  });

  // Step 1: Calculate base layers from depth analysis
  // Find max upstream distance to determine hub layer position
  let maxUpstreamDistance = 0;
  depthAnalysis.nodeDepths.forEach((info) => {
    if (info.depthGroup === "UPSTREAM" && info.distanceToOrchestrator > 0) {
      maxUpstreamDistance = Math.max(maxUpstreamDistance, info.distanceToOrchestrator);
    }
  });
  
  // Hub layer: entry layer (0) + 1 + max upstream distance
  // This ensures enough room for all upstream nodes above the hub
  const hubLayer = 1 + maxUpstreamDistance;

  // Step 2: Assign initial layers based on depth analysis
  depthAnalysis.nodeDepths.forEach((info, nodeId) => {
    const { depthGroup, distanceToOrchestrator, distanceFromOrchestrator } = info;
    
    let layer: number;
    
    switch (depthGroup) {
      case "PINNED_TOP":
        layer = ENTRY_LAYER; // Always at top
        break;
      case "PINNED_BOTTOM":
        layer = Infinity; // Will be set to max + 1 later
        break;
      case "HUB":
        layer = hubLayer;
        break;
      case "UPSTREAM":
        // Place above hub, distance determines how far above
        // Higher distance = further from hub = lower layer number
        layer = Math.max(1, hubLayer - distanceToOrchestrator);
        break;
      case "DOWNSTREAM":
        // Place below hub, distance determines how far below
        layer = hubLayer + distanceFromOrchestrator;
        break;
      case "CYCLIC":
        // Place at hub level, with slight offset based on asymmetry
        const diff = distanceFromOrchestrator - distanceToOrchestrator;
        if (Math.abs(diff) <= 1) {
          layer = hubLayer;
        } else {
          // Slight offset for highly asymmetric cyclic nodes
          layer = hubLayer + Math.sign(diff);
        }
        break;
      case "ISOLATED":
        // Default to hub level
        layer = hubLayer;
        break;
      default:
        layer = hubLayer;
    }
    
    nodeToLayer.set(nodeId, layer);
  });

  // Step 3: Refine layers using edge constraints
  // Ensure proper ordering for edges (source should be above or same as target)
  const maxIterations = nodes.size * 2;
  let iterations = 0;
  let changed = true;

  while (changed && iterations < maxIterations) {
    changed = false;
    iterations++;

    edges.forEach((edge) => {
      const edgeKey = `${edge.source}::${edge.target}`;
      if (backEdges.has(edgeKey)) return;
      
      const sourceLayer = nodeToLayer.get(edge.source);
      const targetLayer = nodeToLayer.get(edge.target);
      
      if (sourceLayer === undefined || targetLayer === undefined) return;
      
      // Skip if target is pinned to bottom
      if (isPinnedBottom(edge.target, constraints)) return;
      
      // Skip if source is pinned to top
      if (isPinnedTop(edge.source, constraints)) return;

      // Ensure target is at least one layer below source
      if (targetLayer <= sourceLayer) {
        // Check depth groups to decide which to move
        const sourceDepth = depthAnalysis.nodeDepths.get(edge.source);
        const targetDepth = depthAnalysis.nodeDepths.get(edge.target);
        
        if (!sourceDepth || !targetDepth) return;
        
        const sourceBand = DEPTH_GROUP_BANDS[sourceDepth.depthGroup];
        const targetBand = DEPTH_GROUP_BANDS[targetDepth.depthGroup];
        
        if (targetBand > sourceBand) {
          // Target should be below source - push target down
          nodeToLayer.set(edge.target, sourceLayer + 1);
          changed = true;
        } else if (sourceBand > targetBand) {
          // This is a back-edge in terms of depth - skip
        } else {
          // Same band - push target down
          nodeToLayer.set(edge.target, sourceLayer + 1);
          changed = true;
        }
      }
    });
  }

  // Step 4: Assign exit nodes to max layer + 1
  let currentMaxLayer = 0;
  nodeToLayer.forEach((layer, nodeId) => {
    if (!isPinnedBottom(nodeId, constraints) && layer !== Infinity) {
      currentMaxLayer = Math.max(currentMaxLayer, layer);
    }
  });

  const exitLayer = currentMaxLayer + 1;
  nodeToLayer.forEach((layer, nodeId) => {
    if (layer === Infinity || isPinnedBottom(nodeId, constraints)) {
      nodeToLayer.set(nodeId, exitLayer);
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

/**
 * Validates that layer assignment respects depth group stratification
 * Returns violations if any
 */
export function validateDepthStratification(
  layerAssignment: LayerAssignment,
  depthAnalysis: DepthAnalysis
): { valid: boolean; violations: string[] } {
  const violations: string[] = [];
  const { nodeToLayer } = layerAssignment;
  
  // Find hub layer(s)
  const hubLayers: number[] = [];
  depthAnalysis.hubNodes.forEach((hubId) => {
    const layer = nodeToLayer.get(hubId);
    if (layer !== undefined) {
      hubLayers.push(layer);
    }
  });
  
  if (hubLayers.length === 0) {
    // No hub, can't validate stratification
    return { valid: true, violations: [] };
  }
  
  const minHubLayer = Math.min(...hubLayers);
  const maxHubLayer = Math.max(...hubLayers);
  
  // Check each node's position relative to hub
  depthAnalysis.nodeDepths.forEach((info, nodeId) => {
    const layer = nodeToLayer.get(nodeId);
    if (layer === undefined) return;
    
    const { depthGroup } = info;
    
    switch (depthGroup) {
      case "UPSTREAM":
        if (layer >= minHubLayer) {
          violations.push(
            `UPSTREAM node '${nodeId}' at layer ${layer} should be above hub layer ${minHubLayer}`
          );
        }
        break;
      case "DOWNSTREAM":
        if (layer <= maxHubLayer) {
          violations.push(
            `DOWNSTREAM node '${nodeId}' at layer ${layer} should be below hub layer ${maxHubLayer}`
          );
        }
        break;
      // CYCLIC and ISOLATED nodes are flexible
    }
  });
  
  return {
    valid: violations.length === 0,
    violations,
  };
}
