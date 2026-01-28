/**
 * Graph Layout Optimizer - Main Entry Point
 * 
 * This module orchestrates the graph layout pipeline:
 * 1. Graph Analysis - Extract structure, classify roles, detect cycles
 * 2. Constraints - Apply hard invariants (entry top, exit bottom)
 * 3. Layering - Assign nodes to layers with cycle breaking
 * 4. Ordering - Minimize crossings with barycenter sweeps
 * 5. Positioning - Compute final X/Y coordinates
 * 
 * INVARIANTS (ABSOLUTE - never violated):
 * 1. Entry nodes (user_question) are ALWAYS at the top (smallest Y)
 * 2. Exit nodes (final_answer) are ALWAYS at the bottom (largest Y)
 * 
 * Mental Model:
 * - Y axis (vertical) = semantic flow: input → processing → output
 * - X axis (horizontal) = structural complexity: spread cycles/agents
 */

// Re-export types
export * from "./types";

// Import modules
import { analyzeGraph, findNodesByRole, computeDepthAnalysis } from "./graphAnalysis";
import { createConstraints, createLayoutBounds } from "./constraints";
import { assignLayers, compactLayers, assignLayersWithDepth } from "./layering";
import { minimizeCrossings, centerOrchestrators, applyStarGroupOrdering, applyFullOrdering } from "./ordering";
import { computePositions, toReactFlowPosition } from "./positioning";

import {
  PlanItem,
  NodeDefinition,
  LayoutConfig,
  LayoutResult,
  LayoutMetadata,
  DEFAULT_LAYOUT_CONFIG,
  DepthGroup,
  DepthAnalysis,
} from "./types";

// ============================================================================
// Main Layout Function
// ============================================================================

/**
 * Computes optimized node positions for a directed graph
 * 
 * @param plan - Array of plan items defining the graph structure
 * @param nodeMap - Map of node RIDs to node definitions
 * @param config - Optional layout configuration
 * @returns Layout result with positions and metadata
 */
export function computeOptimizedLayout(
  plan: PlanItem[],
  nodeMap: Record<string, NodeDefinition>,
  config: Partial<LayoutConfig> = {}
): LayoutResult {
  const fullConfig: LayoutConfig = { ...DEFAULT_LAYOUT_CONFIG, ...config };

  // Handle empty input
  if (!plan || plan.length === 0) {
    const emptyDepthAnalysis: DepthAnalysis = {
      nodeDepths: new Map(),
      groupedNodes: new Map(),
      hubNodes: [],
      isMultiHub: false,
    };
    return {
      positions: new Map(),
      layers: new Map(),
      cycleGroups: new Map(),
      starGroups: [],
      depthAnalysis: emptyDepthAnalysis,
      metadata: {
        entryNodes: [],
        exitNodes: [],
        orchestratorNodes: [],
        cycleCount: 0,
        crossingCount: 0,
        starGroupCount: 0,
        depthGroupCounts: {
          UPSTREAM: 0,
          DOWNSTREAM: 0,
          CYCLIC: 0,
          ISOLATED: 0,
          HUB: 0,
          PINNED_TOP: 0,
          PINNED_BOTTOM: 0,
        },
      },
    };
  }

  // ========================================
  // Step 1: Graph Analysis
  // ========================================
  const graphStructure = analyzeGraph(plan, nodeMap);
  const { nodes, edges, bidirectionalPairs, cycles, roles, starGroups, depthAnalysis } = graphStructure;

  // ========================================
  // Step 2: Create Constraints
  // ========================================
  const constraints = createConstraints(roles);

  // ========================================
  // Step 3: Layer Assignment (Depth-Aware)
  // ========================================
  // Use depth-aware layer assignment for better vertical stratification
  // This ensures UPSTREAM nodes are above the hub, DOWNSTREAM below
  const layerAssignment = assignLayersWithDepth(
    nodes,
    edges,
    roles,
    constraints,
    cycles,
    depthAnalysis
  );
  
  // Compact layers to remove gaps
  const compactedLayers = compactLayers(layerAssignment, constraints);

  // ========================================
  // Step 4: Crossing Minimization
  // ========================================
  const orderingResult = minimizeCrossings(
    compactedLayers,
    edges,
    roles,
    constraints
  );

  // Center orchestrators if configured
  let finalOrdering = orderingResult.orderedLayers;
  if (fullConfig.orchestratorCentric) {
    finalOrdering = centerOrchestrators(
      orderingResult.orderedLayers,
      roles,
      constraints
    );
  }

  // ========================================
  // Step 4.5: Full Ordering (Star Groups + Depth Groups)
  // ========================================
  // Apply comprehensive ordering that considers:
  // 1. Star group symmetry (spokes distributed around hub)
  // 2. Depth group clustering (same semantic band nodes together)
  // 3. Cross-group distribution (prevent clumping)
  finalOrdering = applyFullOrdering(
    finalOrdering,
    starGroups,
    compactedLayers.nodeToLayer,
    depthAnalysis
  );

  // ========================================
  // Step 5: Position Computation (Depth-Aware)
  // ========================================
  const positions = computePositions(
    finalOrdering,
    edges,
    bidirectionalPairs,
    cycles,
    starGroups,
    roles,
    constraints,
    fullConfig,
    depthAnalysis
  );

  // ========================================
  // Build Result
  // ========================================
  
  // Build cycle groups map
  const cycleGroups = new Map<string, string[]>();
  cycles.forEach((cycle, index) => {
    cycleGroups.set(`cycle-${index}`, cycle);
  });

  // Build depth group counts
  const depthGroupCounts: Record<DepthGroup, number> = {
    UPSTREAM: 0,
    DOWNSTREAM: 0,
    CYCLIC: 0,
    ISOLATED: 0,
    HUB: 0,
    PINNED_TOP: 0,
    PINNED_BOTTOM: 0,
  };
  
  depthAnalysis.groupedNodes.forEach((nodes, group) => {
    depthGroupCounts[group] = nodes.length;
  });

  // Build metadata
  const metadata: LayoutMetadata = {
    entryNodes: findNodesByRole(roles, "entry"),
    exitNodes: findNodesByRole(roles, "exit"),
    orchestratorNodes: findNodesByRole(roles, "orchestrator"),
    cycleCount: cycles.length,
    crossingCount: orderingResult.crossingCount,
    starGroupCount: starGroups.length,
    depthGroupCounts,
  };

  return {
    positions,
    layers: finalOrdering,
    cycleGroups,
    starGroups,
    depthAnalysis,
    metadata,
  };
}

// ============================================================================
// Utility Exports
// ============================================================================

/**
 * Converts layout result to React Flow position format
 */
export function getReactFlowPositions(
  layoutResult: LayoutResult
): Record<string, { x: number; y: number }> {
  return toReactFlowPosition(layoutResult.positions);
}

// Re-export individual modules for advanced usage
export { 
  analyzeGraph, 
  findNodesByRole, 
  detectStarGroups, 
  isInStarGroup, 
  isStarHub, 
  isStarSpoke,
  computeDepthAnalysis,
  getNodeDepthGroup,
  getSemanticDepth,
  areDepthGroupsCompatible,
} from "./graphAnalysis";
export { 
  createConstraints, 
  createLayoutBounds, 
  validatePositions,
  DEPTH_GROUP_BANDS,
  getDepthGroupBand,
  compareDepthGroups,
  wouldViolateDepthStratification,
  computeIdealLayers,
} from "./constraints";
export { assignLayers, compactLayers, assignLayersWithDepth, validateDepthStratification } from "./layering";
export { minimizeCrossings, centerOrchestrators, applyStarGroupOrdering, applyFullOrdering, applyDepthGroupOrdering } from "./ordering";
export { 
  computePositions, 
  toReactFlowPosition, 
  snapToGrid, 
  applyStarGroupPositioning,
  applyDepthGroupSpacing,
  balanceEdgeLengths,
  preventHorizontalOutliers,
} from "./positioning";
