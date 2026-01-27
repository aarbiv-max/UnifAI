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
  StarGroup,
  DepthAnalysis,
  DepthGroup,
} from "./types";
import { isPinnedTop, isPinnedBottom, getDepthGroupBand, DEPTH_GROUP_BANDS } from "./constraints";

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

// ============================================================================
// Star Group Ordering
// ============================================================================

/**
 * Applies symmetric ordering for star group spokes
 * 
 * This function distributes star spokes evenly around their hub,
 * preventing barycenter optimization from collapsing symmetric siblings.
 * 
 * The ordering strategy:
 * - Spokes are split evenly left/right around the hub
 * - Alternating placement: upper-left, upper-right, lower-left, lower-right
 * - This maintains visual balance and roughly equal edge lengths
 * 
 * @param orderedLayers - Current layer ordering
 * @param starGroups - Detected star groups
 * @param nodeToLayer - Layer assignment for each node
 * @returns Updated layer ordering with symmetric spoke distribution
 */
export function applyStarGroupOrdering(
  orderedLayers: Map<number, string[]>,
  starGroups: StarGroup[],
  nodeToLayer: Map<string, number>
): Map<number, string[]> {
  if (starGroups.length === 0) {
    return orderedLayers;
  }

  const result = new Map<number, string[]>();
  orderedLayers.forEach((nodes, layer) => {
    result.set(layer, [...nodes]);
  });

  // Process each star group
  starGroups.forEach((starGroup) => {
    const { hubId, spokeIds } = starGroup;
    const hubLayer = nodeToLayer.get(hubId);
    
    if (hubLayer === undefined) return;

    // Group spokes by their layer
    const spokesByLayer = new Map<number, string[]>();
    spokeIds.forEach((spokeId) => {
      const spokeLayer = nodeToLayer.get(spokeId);
      if (spokeLayer === undefined) return;
      
      if (!spokesByLayer.has(spokeLayer)) {
        spokesByLayer.set(spokeLayer, []);
      }
      spokesByLayer.get(spokeLayer)!.push(spokeId);
    });

    // For each layer with spokes, distribute them symmetrically
    spokesByLayer.forEach((layerSpokes, layer) => {
      const currentOrder = result.get(layer);
      if (!currentOrder) return;

      // Find non-spoke nodes in this layer
      const spokeSet = new Set(layerSpokes);
      const nonSpokes = currentOrder.filter((n) => !spokeSet.has(n));
      
      // If there are no non-spokes, just distribute the spokes evenly
      if (nonSpokes.length === 0) {
        // Distribute spokes in alternating left/right pattern
        const distributed = distributeSpokesSymmetrically(layerSpokes);
        result.set(layer, distributed);
        return;
      }

      // Find the hub's position in its layer to align spokes
      const hubLayerNodes = result.get(hubLayer) || [];
      const hubIndex = hubLayerNodes.indexOf(hubId);
      const hubPosition = hubIndex >= 0 ? hubIndex / Math.max(1, hubLayerNodes.length - 1) : 0.5;

      // Distribute spokes around the hub's relative position
      const distributed = distributeSpokesAroundCenter(
        layerSpokes,
        nonSpokes,
        hubPosition
      );
      result.set(layer, distributed);
    });
  });

  return result;
}

/**
 * Distributes spokes symmetrically when they are alone in a layer
 */
function distributeSpokesSymmetrically(spokes: string[]): string[] {
  if (spokes.length <= 1) return spokes;

  const result: string[] = [];
  const leftSpokes: string[] = [];
  const rightSpokes: string[] = [];

  // Alternate between left and right
  spokes.forEach((spoke, index) => {
    if (index % 2 === 0) {
      leftSpokes.push(spoke);
    } else {
      rightSpokes.push(spoke);
    }
  });

  // Combine: left spokes (in order) + right spokes (in order)
  result.push(...leftSpokes, ...rightSpokes);

  return result;
}

/**
 * Distributes spokes around a center position with non-spoke nodes
 */
function distributeSpokesAroundCenter(
  spokes: string[],
  nonSpokes: string[],
  centerPosition: number
): string[] {
  if (spokes.length === 0) return nonSpokes;
  if (spokes.length === 1) {
    // Single spoke: place at center position
    const insertIndex = Math.round(centerPosition * nonSpokes.length);
    const result = [...nonSpokes];
    result.splice(insertIndex, 0, spokes[0]);
    return result;
  }

  // Split spokes into left and right groups
  const leftSpokes: string[] = [];
  const rightSpokes: string[] = [];

  spokes.forEach((spoke, index) => {
    if (index % 2 === 0) {
      leftSpokes.push(spoke);
    } else {
      rightSpokes.push(spoke);
    }
  });

  // Calculate insertion points for balanced distribution
  const totalNodes = nonSpokes.length + spokes.length;
  const leftInsertPoint = Math.floor(totalNodes * 0.25);
  const rightInsertPoint = Math.ceil(totalNodes * 0.75);

  // Build result with spokes distributed symmetrically
  const result: string[] = [];
  let spokeLeftIdx = 0;
  let spokeRightIdx = 0;
  let nonSpokeIdx = 0;
  
  for (let i = 0; i < totalNodes; i++) {
    // Determine if this position should be a left spoke, right spoke, or non-spoke
    const isLeftRegion = i < totalNodes / 2;
    const isRightRegion = i >= totalNodes / 2;

    if (isLeftRegion && spokeLeftIdx < leftSpokes.length) {
      // Place left spokes in the left region
      const spokePositionInRegion = (spokeLeftIdx + 1) / (leftSpokes.length + 1);
      const expectedPosition = Math.floor(spokePositionInRegion * (totalNodes / 2));
      
      if (i >= expectedPosition) {
        result.push(leftSpokes[spokeLeftIdx]);
        spokeLeftIdx++;
        continue;
      }
    }

    if (isRightRegion && spokeRightIdx < rightSpokes.length) {
      // Place right spokes in the right region
      const regionStart = totalNodes / 2;
      const positionInRegion = i - regionStart;
      const spokePositionInRegion = (spokeRightIdx + 1) / (rightSpokes.length + 1);
      const expectedPosition = Math.floor(spokePositionInRegion * (totalNodes / 2));
      
      if (positionInRegion >= expectedPosition) {
        result.push(rightSpokes[spokeRightIdx]);
        spokeRightIdx++;
        continue;
      }
    }

    // Fill with non-spokes
    if (nonSpokeIdx < nonSpokes.length) {
      result.push(nonSpokes[nonSpokeIdx]);
      nonSpokeIdx++;
    }
  }

  // Add any remaining nodes
  while (spokeLeftIdx < leftSpokes.length) {
    result.push(leftSpokes[spokeLeftIdx++]);
  }
  while (spokeRightIdx < rightSpokes.length) {
    result.push(rightSpokes[spokeRightIdx++]);
  }
  while (nonSpokeIdx < nonSpokes.length) {
    result.push(nonSpokes[nonSpokeIdx++]);
  }

  return result;
}

/**
 * Checks if any nodes in a layer are part of a star group
 */
export function hasStarNodesInLayer(
  layer: number,
  orderedLayers: Map<number, string[]>,
  starGroups: StarGroup[]
): boolean {
  const nodes = orderedLayers.get(layer) || [];
  const allStarNodes = new Set<string>();

  starGroups.forEach((group) => {
    allStarNodes.add(group.hubId);
    group.spokeIds.forEach((s) => allStarNodes.add(s));
  });

  return nodes.some((n) => allStarNodes.has(n));
}

// ============================================================================
// Depth Group-Aware Ordering
// ============================================================================

/**
 * Applies depth group-aware ordering within layers
 * 
 * This function ensures that nodes in the same layer are ordered by their
 * depth group, with nodes from the same depth group clustered together.
 * This prevents visual confusion where nodes with different semantic roles
 * appear intermixed.
 * 
 * Ordering priority within a layer:
 * 1. Depth group band (UPSTREAM < HUB/CYCLIC < DOWNSTREAM)
 * 2. Semantic depth within group (closer to hub = more central)
 * 3. Original order (stability)
 * 
 * @param orderedLayers - Current layer ordering
 * @param depthAnalysis - Depth analysis for the graph
 * @returns Updated layer ordering with depth group clustering
 */
export function applyDepthGroupOrdering(
  orderedLayers: Map<number, string[]>,
  depthAnalysis: DepthAnalysis
): Map<number, string[]> {
  const result = new Map<number, string[]>();

  orderedLayers.forEach((nodes, layer) => {
    if (nodes.length <= 1) {
      result.set(layer, [...nodes]);
      return;
    }

    // Sort nodes within layer by depth group and semantic depth
    const sortedNodes = [...nodes].sort((a, b) => {
      const depthA = depthAnalysis.nodeDepths.get(a);
      const depthB = depthAnalysis.nodeDepths.get(b);

      if (!depthA || !depthB) return 0;

      // First, sort by depth group band
      const bandA = DEPTH_GROUP_BANDS[depthA.depthGroup];
      const bandB = DEPTH_GROUP_BANDS[depthB.depthGroup];

      if (bandA !== bandB) {
        return bandA - bandB;
      }

      // Within the same band, sort by semantic depth
      // (closer to hub = lower absolute value = more central)
      const absDepthA = Math.abs(depthA.semanticDepth);
      const absDepthB = Math.abs(depthB.semanticDepth);

      if (absDepthA !== absDepthB) {
        return absDepthA - absDepthB;
      }

      // Stable sort by original position
      return nodes.indexOf(a) - nodes.indexOf(b);
    });

    result.set(layer, sortedNodes);
  });

  return result;
}

/**
 * Distributes nodes within a layer to prevent cross-depth-group clustering
 * 
 * When nodes from different depth groups are in the same layer (which can
 * happen with complex graphs), this ensures they are spread out horizontally
 * rather than clustered together.
 * 
 * @param orderedLayers - Current layer ordering
 * @param depthAnalysis - Depth analysis for the graph
 * @returns Updated layer ordering with better distribution
 */
export function distributeDepthGroupsInLayer(
  orderedLayers: Map<number, string[]>,
  depthAnalysis: DepthAnalysis
): Map<number, string[]> {
  const result = new Map<number, string[]>();

  orderedLayers.forEach((nodes, layer) => {
    if (nodes.length <= 2) {
      result.set(layer, [...nodes]);
      return;
    }

    // Group nodes by their depth group
    const groupedByDepth = new Map<DepthGroup, string[]>();
    
    nodes.forEach((nodeId) => {
      const depthInfo = depthAnalysis.nodeDepths.get(nodeId);
      const group = depthInfo?.depthGroup || "ISOLATED";
      
      if (!groupedByDepth.has(group)) {
        groupedByDepth.set(group, []);
      }
      groupedByDepth.get(group)!.push(nodeId);
    });

    // If all nodes are in the same group, no need to redistribute
    if (groupedByDepth.size === 1) {
      result.set(layer, [...nodes]);
      return;
    }

    // Interleave nodes from different groups for better distribution
    // This prevents "clumping" of same-group nodes on one side
    const distributed = interleaveDepthGroups(groupedByDepth, depthAnalysis);
    result.set(layer, distributed);
  });

  return result;
}

/**
 * Interleaves nodes from different depth groups for balanced horizontal distribution
 */
function interleaveDepthGroups(
  groupedByDepth: Map<DepthGroup, string[]>,
  depthAnalysis: DepthAnalysis
): string[] {
  const result: string[] = [];
  
  // Sort groups by band (UPSTREAM groups first, then HUB/CYCLIC, then DOWNSTREAM)
  const sortedGroups = Array.from(groupedByDepth.keys()).sort((a, b) => {
    return DEPTH_GROUP_BANDS[a] - DEPTH_GROUP_BANDS[b];
  });

  // Collect nodes with their semantic depths for fine-grained ordering
  const allNodes: Array<{ nodeId: string; group: DepthGroup; semanticDepth: number }> = [];
  
  sortedGroups.forEach((group) => {
    const nodes = groupedByDepth.get(group) || [];
    nodes.forEach((nodeId) => {
      const depthInfo = depthAnalysis.nodeDepths.get(nodeId);
      allNodes.push({
        nodeId,
        group,
        semanticDepth: depthInfo?.semanticDepth || 0,
      });
    });
  });

  // Sort by semantic depth (maintaining group clustering but with depth ordering)
  allNodes.sort((a, b) => {
    // Primary: group band
    const bandA = DEPTH_GROUP_BANDS[a.group];
    const bandB = DEPTH_GROUP_BANDS[b.group];
    if (bandA !== bandB) return bandA - bandB;
    
    // Secondary: semantic depth
    return a.semanticDepth - b.semanticDepth;
  });

  // Build result with balanced left/right distribution within groups
  const leftSide: string[] = [];
  const center: string[] = [];
  const rightSide: string[] = [];

  // Distribute: UPSTREAM to left, HUB/CYCLIC to center, DOWNSTREAM to right
  allNodes.forEach((item, index) => {
    const band = DEPTH_GROUP_BANDS[item.group];
    
    if (band < DEPTH_GROUP_BANDS["HUB"]) {
      // UPSTREAM - distribute between left and center-left
      if (index % 2 === 0) {
        leftSide.push(item.nodeId);
      } else {
        leftSide.unshift(item.nodeId);
      }
    } else if (band > DEPTH_GROUP_BANDS["HUB"]) {
      // DOWNSTREAM - distribute between center-right and right
      if (index % 2 === 0) {
        rightSide.push(item.nodeId);
      } else {
        rightSide.unshift(item.nodeId);
      }
    } else {
      // HUB/CYCLIC/ISOLATED - keep in center
      center.push(item.nodeId);
    }
  });

  // Combine: left + center + right
  result.push(...leftSide, ...center, ...rightSide);

  return result;
}

/**
 * Combined ordering that applies both star group and depth group optimizations
 * 
 * Order of operations:
 * 1. Apply depth group ordering (cluster by semantic band)
 * 2. Apply star group ordering (symmetric spoke distribution)
 * 3. Distribute mixed groups (prevent clumping)
 */
export function applyFullOrdering(
  orderedLayers: Map<number, string[]>,
  starGroups: StarGroup[],
  nodeToLayer: Map<string, number>,
  depthAnalysis: DepthAnalysis
): Map<number, string[]> {
  // Step 1: Apply depth group ordering
  let result = applyDepthGroupOrdering(orderedLayers, depthAnalysis);

  // Step 2: Apply star group ordering (if any star groups exist)
  if (starGroups.length > 0) {
    result = applyStarGroupOrdering(result, starGroups, nodeToLayer);
  }

  // Step 3: Distribute mixed depth groups within layers
  result = distributeDepthGroupsInLayer(result, depthAnalysis);

  return result;
}
