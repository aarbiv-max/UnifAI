/**
 * Constraints Module
 * 
 * Responsible for:
 * - Hard layout constraints (input at top, output at bottom)
 * - Node pinning logic
 * - Boundary enforcement
 * 
 * INVARIANTS (these are ABSOLUTE and must NEVER be violated):
 * 1. Entry nodes (user_question) MUST have the smallest Y coordinate
 * 2. Exit nodes (final_answer) MUST have the largest Y coordinate
 * 3. These constraints override ALL other layout optimizations
 */

import {
  NodeRole,
  NodeConstraint,
  ConstraintType,
  LayoutBounds,
  Position,
} from "./types";

// ============================================================================
// Constraint Constants
// ============================================================================

/** Layer reserved for entry nodes (smallest layer number = top) */
export const ENTRY_LAYER = 0;

/** Priority levels for constraints */
export const CONSTRAINT_PRIORITY = {
  ABSOLUTE: 1000,  // Entry/Exit constraints - cannot be overridden
  HIGH: 100,       // Important but can be adjusted
  NORMAL: 10,      // Standard constraint
  LOW: 1,          // Suggestion only
} as const;

// ============================================================================
// Constraint Creation
// ============================================================================

/**
 * Creates constraints for all nodes based on their roles
 * Entry nodes get pin_top, Exit nodes get pin_bottom
 */
export function createConstraints(
  roles: Map<string, NodeRole>
): NodeConstraint[] {
  const constraints: NodeConstraint[] = [];

  roles.forEach((role, nodeId) => {
    switch (role) {
      case "entry":
        constraints.push({
          nodeId,
          type: "pin_top",
          priority: CONSTRAINT_PRIORITY.ABSOLUTE,
        });
        break;
      case "exit":
        constraints.push({
          nodeId,
          type: "pin_bottom",
          priority: CONSTRAINT_PRIORITY.ABSOLUTE,
        });
        break;
      default:
        constraints.push({
          nodeId,
          type: "none",
          priority: CONSTRAINT_PRIORITY.NORMAL,
        });
    }
  });

  return constraints;
}

/**
 * Creates layout bounds based on constraints
 */
export function createLayoutBounds(
  constraints: NodeConstraint[]
): LayoutBounds {
  const reservedTop = new Set<string>();
  const reservedBottom = new Set<string>();

  constraints.forEach((constraint) => {
    if (constraint.type === "pin_top") {
      reservedTop.add(constraint.nodeId);
    } else if (constraint.type === "pin_bottom") {
      reservedBottom.add(constraint.nodeId);
    }
  });

  return {
    minY: 0,
    maxY: Infinity, // Will be computed during positioning
    reservedTop,
    reservedBottom,
  };
}

// ============================================================================
// Constraint Checking
// ============================================================================

/**
 * Checks if a node is pinned (cannot be moved)
 */
export function isPinned(
  nodeId: string,
  constraints: NodeConstraint[]
): boolean {
  const constraint = constraints.find((c) => c.nodeId === nodeId);
  return constraint?.type === "pin_top" || constraint?.type === "pin_bottom";
}

/**
 * Checks if a node is pinned to top
 */
export function isPinnedTop(
  nodeId: string,
  constraints: NodeConstraint[]
): boolean {
  const constraint = constraints.find((c) => c.nodeId === nodeId);
  return constraint?.type === "pin_top";
}

/**
 * Checks if a node is pinned to bottom
 */
export function isPinnedBottom(
  nodeId: string,
  constraints: NodeConstraint[]
): boolean {
  const constraint = constraints.find((c) => c.nodeId === nodeId);
  return constraint?.type === "pin_bottom";
}

/**
 * Gets the constraint type for a node
 */
export function getConstraintType(
  nodeId: string,
  constraints: NodeConstraint[]
): ConstraintType {
  const constraint = constraints.find((c) => c.nodeId === nodeId);
  return constraint?.type || "none";
}

// ============================================================================
// Layer Constraint Enforcement
// ============================================================================

/**
 * Enforces layer constraints on a layer assignment
 * - Entry nodes are forced to layer 0 (top)
 * - Exit nodes are forced to max layer (bottom)
 * - Other nodes are shifted to make room if needed
 */
export function enforceLayerConstraints(
  nodeToLayer: Map<string, number>,
  constraints: NodeConstraint[]
): Map<string, number> {
  const result = new Map(nodeToLayer);
  
  // Find current min and max layers
  let minLayer = Infinity;
  let maxLayer = -Infinity;
  result.forEach((layer) => {
    minLayer = Math.min(minLayer, layer);
    maxLayer = Math.max(maxLayer, layer);
  });

  // Identify pinned nodes
  const pinnedTop: string[] = [];
  const pinnedBottom: string[] = [];
  
  constraints.forEach((constraint) => {
    if (constraint.type === "pin_top") {
      pinnedTop.push(constraint.nodeId);
    } else if (constraint.type === "pin_bottom") {
      pinnedBottom.push(constraint.nodeId);
    }
  });

  // INVARIANT 1: Force all entry nodes to layer 0
  pinnedTop.forEach((nodeId) => {
    result.set(nodeId, 0);
  });

  // Shift all non-pinned-top nodes down by 1 if they were at layer 0
  // This ensures entry nodes are alone at the top
  if (pinnedTop.length > 0) {
    result.forEach((layer, nodeId) => {
      if (!pinnedTop.includes(nodeId) && layer <= 0) {
        result.set(nodeId, layer + 1);
      }
    });
  }

  // Recalculate max layer after shifts
  maxLayer = -Infinity;
  result.forEach((layer, nodeId) => {
    if (!pinnedBottom.includes(nodeId)) {
      maxLayer = Math.max(maxLayer, layer);
    }
  });

  // INVARIANT 2: Force all exit nodes to max layer + 1
  const exitLayer = maxLayer + 1;
  pinnedBottom.forEach((nodeId) => {
    result.set(nodeId, exitLayer);
  });

  return result;
}

// ============================================================================
// Position Constraint Enforcement
// ============================================================================

/**
 * Validates that positions satisfy all constraints
 * Returns a list of violations if any
 */
export function validatePositions(
  positions: Map<string, Position>,
  constraints: NodeConstraint[]
): { valid: boolean; violations: string[] } {
  const violations: string[] = [];

  // Find min and max Y coordinates
  let minY = Infinity;
  let maxY = -Infinity;
  let minYNodes: string[] = [];
  let maxYNodes: string[] = [];

  positions.forEach((pos, nodeId) => {
    if (pos.y < minY) {
      minY = pos.y;
      minYNodes = [nodeId];
    } else if (pos.y === minY) {
      minYNodes.push(nodeId);
    }

    if (pos.y > maxY) {
      maxY = pos.y;
      maxYNodes = [nodeId];
    } else if (pos.y === maxY) {
      maxYNodes.push(nodeId);
    }
  });

  // Check INVARIANT 1: Entry nodes must be at top (smallest Y)
  constraints.forEach((constraint) => {
    if (constraint.type === "pin_top") {
      const pos = positions.get(constraint.nodeId);
      if (pos && pos.y !== minY) {
        violations.push(
          `Entry node '${constraint.nodeId}' is not at top (Y=${pos.y}, minY=${minY})`
        );
      }
    }
  });

  // Check INVARIANT 2: Exit nodes must be at bottom (largest Y)
  constraints.forEach((constraint) => {
    if (constraint.type === "pin_bottom") {
      const pos = positions.get(constraint.nodeId);
      if (pos && pos.y !== maxY) {
        violations.push(
          `Exit node '${constraint.nodeId}' is not at bottom (Y=${pos.y}, maxY=${maxY})`
        );
      }
    }
  });

  return {
    valid: violations.length === 0,
    violations,
  };
}

/**
 * Forces positions to satisfy constraints
 * This is a last-resort enforcement that may override other optimizations
 */
export function enforcePositionConstraints(
  positions: Map<string, Position>,
  constraints: NodeConstraint[],
  layerSpacing: number
): Map<string, Position> {
  const result = new Map<string, Position>();
  
  // Copy all positions
  positions.forEach((pos, nodeId) => {
    result.set(nodeId, { ...pos });
  });

  // Find pinned nodes
  const pinnedTop: string[] = [];
  const pinnedBottom: string[] = [];
  const unpinned: string[] = [];

  constraints.forEach((constraint) => {
    if (constraint.type === "pin_top") {
      pinnedTop.push(constraint.nodeId);
    } else if (constraint.type === "pin_bottom") {
      pinnedBottom.push(constraint.nodeId);
    } else {
      unpinned.push(constraint.nodeId);
    }
  });

  // Find current Y range of unpinned nodes
  let minUnpinnedY = Infinity;
  let maxUnpinnedY = -Infinity;
  unpinned.forEach((nodeId) => {
    const pos = result.get(nodeId);
    if (pos) {
      minUnpinnedY = Math.min(minUnpinnedY, pos.y);
      maxUnpinnedY = Math.max(maxUnpinnedY, pos.y);
    }
  });

  // Calculate entry Y (above all unpinned nodes)
  const entryY = minUnpinnedY - layerSpacing;

  // Calculate exit Y (below all unpinned nodes)
  const exitY = maxUnpinnedY + layerSpacing;

  // INVARIANT 1: Force entry nodes to top
  pinnedTop.forEach((nodeId) => {
    const pos = result.get(nodeId);
    if (pos) {
      pos.y = entryY;
    }
  });

  // INVARIANT 2: Force exit nodes to bottom
  pinnedBottom.forEach((nodeId) => {
    const pos = result.get(nodeId);
    if (pos) {
      pos.y = exitY;
    }
  });

  return result;
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Gets all nodes that can be freely positioned (not pinned)
 */
export function getMovableNodes(
  nodeIds: string[],
  constraints: NodeConstraint[]
): string[] {
  return nodeIds.filter((nodeId) => !isPinned(nodeId, constraints));
}

/**
 * Checks if a proposed layer violates constraints
 */
export function wouldViolateConstraint(
  nodeId: string,
  proposedLayer: number,
  constraints: NodeConstraint[],
  currentMinLayer: number,
  currentMaxLayer: number
): boolean {
  const constraintType = getConstraintType(nodeId, constraints);

  if (constraintType === "pin_top" && proposedLayer !== ENTRY_LAYER) {
    return true;
  }

  if (constraintType === "pin_bottom" && proposedLayer <= currentMaxLayer) {
    // Exit node must be at the maximum layer
    return true;
  }

  return false;
}
