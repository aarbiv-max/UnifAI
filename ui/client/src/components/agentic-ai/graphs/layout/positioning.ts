/**
 * Positioning Module
 * 
 * Responsible for:
 * - Final X/Y coordinate computation
 * - Grid snapping
 * - Spacing adjustments
 * - Edge overlap avoidance
 * 
 * Coordinate System:
 * - Y axis = semantic flow (vertical): top (min Y) → bottom (max Y)
 * - X axis = structural spread (horizontal): center to sides
 * 
 * INVARIANTS (enforced here):
 * - Entry nodes have smallest Y (top)
 * - Exit nodes have largest Y (bottom)
 */

import {
  Position,
  LayoutConfig,
  NodeRole,
  NodeConstraint,
  LayoutEdge,
  StarGroup,
  SpokePlacement,
  DepthAnalysis,
  DepthGroup,
} from "./types";
import { isPinnedTop, isPinnedBottom, enforcePositionConstraints, validatePositions, DEPTH_GROUP_BANDS } from "./constraints";

// ============================================================================
// Grid Snapping
// ============================================================================

/**
 * Snaps a value to the nearest grid point
 */
export function snapToGrid(value: number, gridSize: number): number {
  return Math.round(value / gridSize) * gridSize;
}

// ============================================================================
// Basic Position Calculation
// ============================================================================

/**
 * Calculates initial positions based on layer ordering
 * Y = layer * layerSpacing (vertical semantic flow)
 * X = centered within layer (horizontal structural spread)
 */
export function calculateInitialPositions(
  orderedLayers: Map<number, string[]>,
  config: LayoutConfig
): Map<string, Position> {
  const positions = new Map<string, Position>();
  const { layerSpacing, nodeSpacing, gridSize } = config;

  orderedLayers.forEach((nodes, layer) => {
    const layerWidth = (nodes.length - 1) * nodeSpacing;
    const startX = -layerWidth / 2;

    nodes.forEach((nodeId, index) => {
      const x = snapToGrid(startX + index * nodeSpacing, gridSize);
      const y = snapToGrid(layer * layerSpacing, gridSize);
      positions.set(nodeId, { x, y });
    });
  });

  return positions;
}

// ============================================================================
// Bidirectional Edge Handling
// ============================================================================

/**
 * Adjusts positions for nodes with bidirectional edges
 * Nodes with bidirectional connections should be vertically aligned
 * to reduce visual clutter
 * 
 * @param skipNodes - Optional set of node IDs to skip (e.g., star group nodes)
 */
export function adjustForBidirectionalEdges(
  positions: Map<string, Position>,
  edges: LayoutEdge[],
  bidirectionalPairs: Set<string>,
  roles: Map<string, NodeRole>,
  constraints: NodeConstraint[],
  config: LayoutConfig,
  skipNodes: Set<string> = new Set()
): void {
  const { gridSize } = config;

  // Find all bidirectional partners
  const partners = new Map<string, string[]>();
  
  edges.forEach((edge) => {
    const edgeKey = `${edge.source}::${edge.target}`;
    if (bidirectionalPairs.has(edgeKey)) {
      if (!partners.has(edge.source)) {
        partners.set(edge.source, []);
      }
      if (!partners.has(edge.target)) {
        partners.set(edge.target, []);
      }
      partners.get(edge.source)!.push(edge.target);
      partners.get(edge.target)!.push(edge.source);
    }
  });

  // Adjust X positions to align bidirectional pairs
  partners.forEach((partnerList, nodeId) => {
    // Skip nodes in star groups (they've been positioned radially)
    if (skipNodes.has(nodeId)) return;

    // Skip pinned nodes
    if (isPinnedTop(nodeId, constraints) || isPinnedBottom(nodeId, constraints)) {
      return;
    }

    const nodePos = positions.get(nodeId);
    if (!nodePos) return;

    partnerList.forEach((partnerId) => {
      // Skip if partner is in star group
      if (skipNodes.has(partnerId)) return;

      const partnerPos = positions.get(partnerId);
      if (!partnerPos) return;

      // If they're at different Y levels, try to align X
      if (nodePos.y !== partnerPos.y) {
        // Calculate average X
        const avgX = (nodePos.x + partnerPos.x) / 2;
        
        // Only adjust the non-orchestrator node
        if (roles.get(nodeId) !== "orchestrator" && 
            !isPinnedTop(nodeId, constraints) && 
            !isPinnedBottom(nodeId, constraints)) {
          nodePos.x = snapToGrid(avgX, gridSize);
        }
      }
    });
  });
}

// ============================================================================
// Cycle Layout
// ============================================================================

/**
 * Adjusts positions for nodes in cycles
 * Cycles are spread horizontally to make the cyclic structure visible
 */
export function adjustForCycles(
  positions: Map<string, Position>,
  cycles: string[][],
  roles: Map<string, NodeRole>,
  constraints: NodeConstraint[],
  config: LayoutConfig
): void {
  const { nodeSpacing, gridSize } = config;

  cycles.forEach((cycle) => {
    if (cycle.length <= 2) return; // Skip simple bidirectional pairs

    // Find the central node (orchestrator if present, otherwise first node)
    const orchestrator = cycle.find((n) => roles.get(n) === "orchestrator");
    const centerNode = orchestrator || cycle[0];
    const centerPos = positions.get(centerNode);
    if (!centerPos) return;

    // Get other nodes in the cycle
    const otherNodes = cycle.filter((n) => n !== centerNode);
    
    // Spread other nodes horizontally around the center
    const spreadRadius = nodeSpacing * 0.6;
    const angleStep = Math.PI / (otherNodes.length + 1);

    otherNodes.forEach((nodeId, index) => {
      // Skip pinned nodes
      if (isPinnedTop(nodeId, constraints) || isPinnedBottom(nodeId, constraints)) {
        return;
      }

      const pos = positions.get(nodeId);
      if (!pos) return;

      // Calculate horizontal offset
      const angle = angleStep * (index + 1) - Math.PI / 2;
      const offsetX = Math.cos(angle) * spreadRadius;
      
      pos.x = snapToGrid(centerPos.x + offsetX, gridSize);
    });
  });
}

// ============================================================================
// Star / Hub-and-Spoke Layout
// ============================================================================

/**
 * Calculates spoke placements for a star group
 * 
 * Spokes are distributed in a balanced pattern:
 * - Split evenly between left and right of hub
 * - Alternating quadrants: upper-left, upper-right, lower-left, lower-right
 * - Equal horizontal distance from hub
 * - Slight vertical offsets for visual separation
 */
export function calculateSpokePlacements(
  starGroup: StarGroup,
  hubPosition: Position,
  config: LayoutConfig
): SpokePlacement[] {
  const { spokeIds } = starGroup;
  const { nodeSpacing, layerSpacing, gridSize } = config;
  
  const placements: SpokePlacement[] = [];
  const spokeCount = spokeIds.length;
  
  if (spokeCount === 0) return placements;

  // Calculate base horizontal offset (distance from hub)
  const baseOffsetX = nodeSpacing * 0.7;
  
  // Calculate vertical offset (slight stagger for visual separation)
  const verticalStagger = layerSpacing * 0.15;

  // Distribute spokes in quadrants
  // Pattern: alternate left/right, then upper/lower
  spokeIds.forEach((spokeId, index) => {
    // Determine quadrant: 0=upper-left, 1=upper-right, 2=lower-left, 3=lower-right
    const isRight = index % 2 === 1;
    const isLower = Math.floor(index / 2) % 2 === 1;
    const quadrant = (isLower ? 2 : 0) + (isRight ? 1 : 0);

    // Calculate offsets
    const pairIndex = Math.floor(index / 2);
    const horizontalMultiplier = isRight ? 1 : -1;
    const verticalMultiplier = isLower ? 1 : -1;

    // Stagger horizontally for nodes in same side
    const horizontalStagger = pairIndex * nodeSpacing * 0.3;
    
    const offsetX = snapToGrid(
      horizontalMultiplier * (baseOffsetX + horizontalStagger),
      gridSize
    );
    const offsetY = snapToGrid(
      verticalMultiplier * verticalStagger * (pairIndex + 1),
      gridSize
    );

    placements.push({
      nodeId: spokeId,
      quadrant,
      offsetX,
      offsetY,
    });
  });

  return placements;
}

/**
 * Applies star group positioning to distribute spokes radially around hubs
 * 
 * This function:
 * - Finds the hub position for each star group
 * - Distributes spokes symmetrically around the hub
 * - Maintains roughly equal edge lengths
 * - Prevents spoke overlap
 */
export function applyStarGroupPositioning(
  positions: Map<string, Position>,
  starGroups: StarGroup[],
  constraints: NodeConstraint[],
  config: LayoutConfig
): void {
  const { gridSize } = config;

  starGroups.forEach((starGroup) => {
    const { hubId, spokeIds } = starGroup;
    
    const hubPos = positions.get(hubId);
    if (!hubPos) return;

    // Calculate spoke placements
    const placements = calculateSpokePlacements(starGroup, hubPos, config);

    // Apply placements
    placements.forEach((placement) => {
      const { nodeId, offsetX, offsetY } = placement;
      
      // Skip if node is pinned
      if (isPinnedTop(nodeId, constraints) || isPinnedBottom(nodeId, constraints)) {
        return;
      }

      const spokePos = positions.get(nodeId);
      if (!spokePos) return;

      // Apply offset from hub position
      // Keep Y based on layer, only adjust X for radial distribution
      spokePos.x = snapToGrid(hubPos.x + offsetX, gridSize);
      
      // Add slight Y adjustment if spoke is in same layer as hub
      if (Math.abs(spokePos.y - hubPos.y) < config.layerSpacing / 2) {
        spokePos.y = snapToGrid(spokePos.y + offsetY, gridSize);
      }
    });
  });
}

/**
 * Fine-tunes star layout to ensure spokes don't overlap
 */
export function preventSpokeOverlap(
  positions: Map<string, Position>,
  starGroups: StarGroup[],
  constraints: NodeConstraint[],
  config: LayoutConfig
): void {
  const { nodeSpacing, gridSize } = config;
  const minDistance = nodeSpacing * 0.8;

  starGroups.forEach((starGroup) => {
    const { spokeIds } = starGroup;

    // Check each pair of spokes
    for (let i = 0; i < spokeIds.length; i++) {
      for (let j = i + 1; j < spokeIds.length; j++) {
        const spokeA = spokeIds[i];
        const spokeB = spokeIds[j];

        // Skip pinned nodes
        if (isPinnedTop(spokeA, constraints) || isPinnedBottom(spokeA, constraints)) continue;
        if (isPinnedTop(spokeB, constraints) || isPinnedBottom(spokeB, constraints)) continue;

        const posA = positions.get(spokeA);
        const posB = positions.get(spokeB);
        if (!posA || !posB) continue;

        // Check if they're too close
        const dx = posB.x - posA.x;
        const dy = posB.y - posA.y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance < minDistance && distance > 0) {
          // Push them apart
          const pushDistance = (minDistance - distance) / 2;
          const angle = Math.atan2(dy, dx);

          posA.x = snapToGrid(posA.x - Math.cos(angle) * pushDistance, gridSize);
          posB.x = snapToGrid(posB.x + Math.cos(angle) * pushDistance, gridSize);
        }
      }
    }
  });
}

// ============================================================================
// Edge Overlap Avoidance
// ============================================================================

interface NodeBounds {
  left: number;
  right: number;
  top: number;
  bottom: number;
  centerX: number;
  centerY: number;
}

const NODE_WIDTH = 220;
const NODE_HEIGHT = 90;
const MARGIN = 20;

/**
 * Gets the bounding box for a node
 */
function getNodeBounds(pos: Position): NodeBounds {
  return {
    left: pos.x - NODE_WIDTH / 2,
    right: pos.x + NODE_WIDTH / 2,
    top: pos.y - NODE_HEIGHT / 2,
    bottom: pos.y + NODE_HEIGHT / 2,
    centerX: pos.x,
    centerY: pos.y,
  };
}

/**
 * Checks if a line segment intersects a rectangle (Liang-Barsky algorithm)
 */
function lineIntersectsRect(
  x1: number, y1: number,
  x2: number, y2: number,
  rect: NodeBounds
): boolean {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const p = [-dx, dx, -dy, dy];
  const q = [
    x1 - rect.left + MARGIN,
    rect.right + MARGIN - x1,
    y1 - rect.top + MARGIN,
    rect.bottom + MARGIN - y1,
  ];

  let t0 = 0;
  let t1 = 1;

  for (let i = 0; i < 4; i++) {
    if (p[i] === 0) {
      if (q[i] < 0) return false;
    } else {
      const t = q[i] / p[i];
      if (p[i] < 0) {
        if (t > t1) return false;
        if (t > t0) t0 = t;
      } else {
        if (t < t0) return false;
        if (t < t1) t1 = t;
      }
    }
  }

  return true;
}

/**
 * Adjusts positions to avoid edges passing through nodes
 */
export function avoidEdgeOverlaps(
  positions: Map<string, Position>,
  edges: LayoutEdge[],
  constraints: NodeConstraint[],
  config: LayoutConfig,
  maxIterations: number = 10
): void {
  const { nodeSpacing, gridSize } = config;
  const shiftAmount = nodeSpacing * 0.5;

  for (let iter = 0; iter < maxIterations; iter++) {
    let moved = false;

    edges.forEach((edge) => {
      const sourcePos = positions.get(edge.source);
      const targetPos = positions.get(edge.target);
      if (!sourcePos || !targetPos) return;

      // Check each node against this edge
      positions.forEach((nodePos, nodeId) => {
        // Skip source and target
        if (nodeId === edge.source || nodeId === edge.target) return;
        
        // Skip pinned nodes
        if (isPinnedTop(nodeId, constraints) || isPinnedBottom(nodeId, constraints)) {
          return;
        }

        const bounds = getNodeBounds(nodePos);
        
        if (lineIntersectsRect(
          sourcePos.x, sourcePos.y,
          targetPos.x, targetPos.y,
          bounds
        )) {
          // Move node away from edge
          const edgeMidX = (sourcePos.x + targetPos.x) / 2;
          const direction = nodePos.x >= edgeMidX ? 1 : -1;
          nodePos.x = snapToGrid(nodePos.x + direction * shiftAmount, gridSize);
          moved = true;
        }
      });
    });

    if (!moved) break;
  }
}

// ============================================================================
// Depth Group-Aware Positioning
// ============================================================================

/**
 * Adjusts horizontal positions based on depth groups to prevent clumping
 * 
 * Nodes in the same depth group within a layer are spread evenly,
 * while nodes in different depth groups are given additional separation.
 * 
 * @param positions - Current positions
 * @param orderedLayers - Layer ordering
 * @param depthAnalysis - Depth analysis results
 * @param config - Layout configuration
 */
export function applyDepthGroupSpacing(
  positions: Map<string, Position>,
  orderedLayers: Map<number, string[]>,
  depthAnalysis: DepthAnalysis,
  config: LayoutConfig
): void {
  const { nodeSpacing, gridSize } = config;
  const groupSeparation = nodeSpacing * 0.3; // Extra space between groups

  orderedLayers.forEach((nodes, layer) => {
    if (nodes.length <= 1) return;

    // Group nodes by depth group
    const groupedNodes = new Map<DepthGroup, string[]>();
    nodes.forEach((nodeId) => {
      const depthInfo = depthAnalysis.nodeDepths.get(nodeId);
      const group = depthInfo?.depthGroup || "ISOLATED";
      
      if (!groupedNodes.has(group)) {
        groupedNodes.set(group, []);
      }
      groupedNodes.get(group)!.push(nodeId);
    });

    // If only one group, no extra spacing needed
    if (groupedNodes.size <= 1) return;

    // Calculate the center X of the layer
    let sumX = 0;
    let count = 0;
    nodes.forEach((nodeId) => {
      const pos = positions.get(nodeId);
      if (pos) {
        sumX += pos.x;
        count++;
      }
    });
    const centerX = count > 0 ? sumX / count : 0;

    // Sort groups by band
    const sortedGroups = Array.from(groupedNodes.keys()).sort((a, b) => {
      return DEPTH_GROUP_BANDS[a] - DEPTH_GROUP_BANDS[b];
    });

    // Redistribute: earlier bands on left, later bands on right
    let currentX = centerX - (sortedGroups.length - 1) * groupSeparation / 2;
    
    sortedGroups.forEach((group, groupIndex) => {
      const groupNodes = groupedNodes.get(group) || [];
      const groupWidth = (groupNodes.length - 1) * nodeSpacing;
      const groupStartX = currentX - groupWidth / 2;

      groupNodes.forEach((nodeId, nodeIndex) => {
        const pos = positions.get(nodeId);
        if (pos) {
          // Position within group
          pos.x = snapToGrid(groupStartX + nodeIndex * nodeSpacing, gridSize);
        }
      });

      currentX += groupWidth + groupSeparation;
    });
  });
}

/**
 * Balances edge lengths within depth groups to minimize variance
 * 
 * This is a secondary optimization that runs after basic positioning.
 * It adjusts node positions to make edge lengths more uniform,
 * which improves visual clarity.
 * 
 * @param positions - Current positions
 * @param edges - All edges
 * @param depthAnalysis - Depth analysis results
 * @param constraints - Layout constraints
 * @param config - Layout configuration
 */
export function balanceEdgeLengths(
  positions: Map<string, Position>,
  edges: LayoutEdge[],
  depthAnalysis: DepthAnalysis,
  constraints: NodeConstraint[],
  config: LayoutConfig,
  maxIterations: number = 5
): void {
  const { nodeSpacing, gridSize } = config;
  const minMove = gridSize;
  const maxMove = nodeSpacing * 0.3;

  for (let iter = 0; iter < maxIterations; iter++) {
    let totalMoved = 0;

    // For each node, calculate the "ideal" position based on edge lengths
    positions.forEach((pos, nodeId) => {
      // Skip pinned nodes
      if (isPinnedTop(nodeId, constraints) || isPinnedBottom(nodeId, constraints)) {
        return;
      }

      const depthInfo = depthAnalysis.nodeDepths.get(nodeId);
      if (!depthInfo) return;

      // Collect all edges connected to this node
      const connectedEdges = edges.filter(
        (e) => e.source === nodeId || e.target === nodeId
      );

      if (connectedEdges.length === 0) return;

      // Calculate edge lengths and their "pull" on the node
      let pullX = 0;
      let pullCount = 0;

      connectedEdges.forEach((edge) => {
        const otherId = edge.source === nodeId ? edge.target : edge.source;
        const otherPos = positions.get(otherId);
        if (!otherPos) return;

        const otherDepth = depthAnalysis.nodeDepths.get(otherId);
        if (!otherDepth) return;

        // Calculate current edge length
        const dx = otherPos.x - pos.x;
        const dy = otherPos.y - pos.y;
        const length = Math.sqrt(dx * dx + dy * dy);

        // Target length based on layer distance
        const targetLength = Math.abs(dy) + nodeSpacing * 0.3;

        // If edge is too long, pull toward other node
        // If too short, push away
        if (length > 0) {
          const lengthDiff = targetLength - length;
          const normalizedPull = (dx / length) * lengthDiff * 0.3;

          // Weight by depth group compatibility
          const sameGroup = depthInfo.depthGroup === otherDepth.depthGroup;
          const weight = sameGroup ? 1.0 : 0.5;

          pullX += normalizedPull * weight;
          pullCount++;
        }
      });

      // Apply averaged pull
      if (pullCount > 0) {
        const avgPull = pullX / pullCount;
        const clampedPull = Math.max(-maxMove, Math.min(maxMove, avgPull));

        if (Math.abs(clampedPull) >= minMove) {
          pos.x = snapToGrid(pos.x + clampedPull, gridSize);
          totalMoved += Math.abs(clampedPull);
        }
      }
    });

    // Stop if no significant movement
    if (totalMoved < minMove * 2) break;
  }
}

/**
 * Prevents nodes from being pushed too far horizontally
 * 
 * This addresses the "randomly far away" failure mode by detecting
 * nodes that are outliers and pulling them back toward the center.
 * 
 * @param positions - Current positions
 * @param orderedLayers - Layer ordering
 * @param constraints - Layout constraints
 * @param config - Layout configuration
 */
export function preventHorizontalOutliers(
  positions: Map<string, Position>,
  orderedLayers: Map<number, string[]>,
  constraints: NodeConstraint[],
  config: LayoutConfig
): void {
  const { nodeSpacing, gridSize } = config;
  const maxDeviation = nodeSpacing * 2; // Maximum deviation from layer median

  orderedLayers.forEach((nodes, layer) => {
    if (nodes.length <= 2) return;

    // Calculate median X for this layer
    const xPositions = nodes
      .map((nodeId) => positions.get(nodeId)?.x)
      .filter((x): x is number => x !== undefined)
      .sort((a, b) => a - b);

    if (xPositions.length === 0) return;

    const medianX = xPositions[Math.floor(xPositions.length / 2)];

    // Check each node for outlier status
    nodes.forEach((nodeId) => {
      // Skip pinned nodes
      if (isPinnedTop(nodeId, constraints) || isPinnedBottom(nodeId, constraints)) {
        return;
      }

      const pos = positions.get(nodeId);
      if (!pos) return;

      const deviation = Math.abs(pos.x - medianX);

      if (deviation > maxDeviation) {
        // Pull back toward median, but not all the way
        const pullBack = (deviation - maxDeviation) * 0.7;
        const direction = pos.x > medianX ? -1 : 1;
        pos.x = snapToGrid(pos.x + direction * pullBack, gridSize);
      }
    });
  });
}

// ============================================================================
// Final Position Computation
// ============================================================================

/**
 * Computes final positions for all nodes
 * This is the main entry point for positioning
 */
export function computePositions(
  orderedLayers: Map<number, string[]>,
  edges: LayoutEdge[],
  bidirectionalPairs: Set<string>,
  cycles: string[][],
  starGroups: StarGroup[],
  roles: Map<string, NodeRole>,
  constraints: NodeConstraint[],
  config: LayoutConfig,
  depthAnalysis?: DepthAnalysis
): Map<string, Position> {
  // Step 1: Calculate initial positions based on layers
  const positions = calculateInitialPositions(orderedLayers, config);

  // Step 2: Apply depth group spacing (if depth analysis available)
  // This ensures nodes in different depth groups are properly separated
  if (depthAnalysis) {
    applyDepthGroupSpacing(positions, orderedLayers, depthAnalysis, config);
  }

  // Step 3: Apply star group positioning (BEFORE other adjustments)
  // This ensures spokes are distributed symmetrically around their hubs
  if (starGroups.length > 0) {
    applyStarGroupPositioning(positions, starGroups, constraints, config);
    preventSpokeOverlap(positions, starGroups, constraints, config);
  }

  // Step 4: Adjust for bidirectional edges (skip nodes in star groups)
  // Star group nodes have already been positioned radially
  const starNodeSet = new Set<string>();
  starGroups.forEach((group) => {
    starNodeSet.add(group.hubId);
    group.spokeIds.forEach((s) => starNodeSet.add(s));
  });

  adjustForBidirectionalEdges(
    positions,
    edges,
    bidirectionalPairs,
    roles,
    constraints,
    config,
    starNodeSet
  );

  // Step 5: Adjust for cycles (skip star group cycles)
  // Only apply to non-star cycles
  const nonStarCycles = cycles.filter((cycle) => {
    return !cycle.some((nodeId) => starNodeSet.has(nodeId));
  });
  adjustForCycles(positions, nonStarCycles, roles, constraints, config);

  // Step 6: Avoid edge overlaps
  avoidEdgeOverlaps(positions, edges, constraints, config);

  // Step 7: Balance edge lengths (if depth analysis available)
  // This minimizes variance in edge lengths within semantic groups
  if (depthAnalysis) {
    balanceEdgeLengths(positions, edges, depthAnalysis, constraints, config);
  }

  // Step 8: Prevent horizontal outliers
  // This addresses the "randomly far away" node problem
  preventHorizontalOutliers(positions, orderedLayers, constraints, config);

  // Step 9: Enforce constraints (INVARIANTS)
  // This is the final guarantee that entry is at top and exit is at bottom
  const constrainedPositions = enforcePositionConstraints(
    positions,
    constraints,
    config.layerSpacing
  );

  // Step 10: Validate (for debugging)
  const validation = validatePositions(constrainedPositions, constraints);
  if (!validation.valid) {
    console.warn("Layout constraint violations:", validation.violations);
  }

  // Step 11: Center the graph around origin
  return centerGraph(constrainedPositions, config.gridSize);
}

// ============================================================================
// Graph Centering
// ============================================================================

/**
 * Centers the entire graph around the origin (0, 0)
 */
function centerGraph(
  positions: Map<string, Position>,
  gridSize: number
): Map<string, Position> {
  if (positions.size === 0) return positions;

  // Find bounding box
  let minX = Infinity, maxX = -Infinity;
  let minY = Infinity, maxY = -Infinity;

  positions.forEach((pos) => {
    minX = Math.min(minX, pos.x);
    maxX = Math.max(maxX, pos.x);
    minY = Math.min(minY, pos.y);
    maxY = Math.max(maxY, pos.y);
  });

  // Calculate center offset
  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;

  // Shift all positions
  const centered = new Map<string, Position>();
  positions.forEach((pos, nodeId) => {
    centered.set(nodeId, {
      x: snapToGrid(pos.x - centerX, gridSize),
      y: snapToGrid(pos.y - centerY, gridSize),
    });
  });

  return centered;
}

// ============================================================================
// Position Utilities
// ============================================================================

/**
 * Gets position in React Flow format
 */
export function toReactFlowPosition(
  positions: Map<string, Position>
): Record<string, { x: number; y: number }> {
  const result: Record<string, { x: number; y: number }> = {};
  positions.forEach((pos, nodeId) => {
    result[nodeId] = { x: pos.x, y: pos.y };
  });
  return result;
}
