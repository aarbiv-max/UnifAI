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
} from "./types";
import { isPinnedTop, isPinnedBottom, enforcePositionConstraints, validatePositions } from "./constraints";

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
 */
export function adjustForBidirectionalEdges(
  positions: Map<string, Position>,
  edges: LayoutEdge[],
  bidirectionalPairs: Set<string>,
  roles: Map<string, NodeRole>,
  constraints: NodeConstraint[],
  config: LayoutConfig
): void {
  const { nodeSpacing, gridSize } = config;

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
    // Skip pinned nodes
    if (isPinnedTop(nodeId, constraints) || isPinnedBottom(nodeId, constraints)) {
      return;
    }

    const nodePos = positions.get(nodeId);
    if (!nodePos) return;

    partnerList.forEach((partnerId) => {
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
  roles: Map<string, NodeRole>,
  constraints: NodeConstraint[],
  config: LayoutConfig
): Map<string, Position> {
  // Step 1: Calculate initial positions based on layers
  const positions = calculateInitialPositions(orderedLayers, config);

  // Step 2: Adjust for bidirectional edges
  adjustForBidirectionalEdges(
    positions,
    edges,
    bidirectionalPairs,
    roles,
    constraints,
    config
  );

  // Step 3: Adjust for cycles
  adjustForCycles(positions, cycles, roles, constraints, config);

  // Step 4: Avoid edge overlaps
  avoidEdgeOverlaps(positions, edges, constraints, config);

  // Step 5: Enforce constraints (INVARIANTS)
  // This is the final guarantee that entry is at top and exit is at bottom
  const constrainedPositions = enforcePositionConstraints(
    positions,
    constraints,
    config.layerSpacing
  );

  // Step 6: Validate (for debugging)
  const validation = validatePositions(constrainedPositions, constraints);
  if (!validation.valid) {
    console.warn("Layout constraint violations:", validation.violations);
  }

  // Step 7: Center the graph around origin
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
