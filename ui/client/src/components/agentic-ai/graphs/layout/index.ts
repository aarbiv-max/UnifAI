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
import { analyzeGraph, findNodesByRole } from "./graphAnalysis";
import { createConstraints, createLayoutBounds } from "./constraints";
import { assignLayers, compactLayers } from "./layering";
import { minimizeCrossings, centerOrchestrators } from "./ordering";
import { computePositions, toReactFlowPosition } from "./positioning";

import {
  PlanItem,
  NodeDefinition,
  LayoutConfig,
  LayoutResult,
  LayoutMetadata,
  DEFAULT_LAYOUT_CONFIG,
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
    return {
      positions: new Map(),
      layers: new Map(),
      cycleGroups: new Map(),
      metadata: {
        entryNodes: [],
        exitNodes: [],
        orchestratorNodes: [],
        cycleCount: 0,
        crossingCount: 0,
      },
    };
  }

  // ========================================
  // Step 1: Graph Analysis
  // ========================================
  const graphStructure = analyzeGraph(plan, nodeMap);
  const { nodes, edges, bidirectionalPairs, cycles, roles } = graphStructure;

  // ========================================
  // Step 2: Create Constraints
  // ========================================
  const constraints = createConstraints(roles);
  const bounds = createLayoutBounds(constraints);

  // ========================================
  // Step 3: Layer Assignment
  // ========================================
  const layerAssignment = assignLayers(
    nodes,
    edges,
    roles,
    constraints,
    cycles
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
  // Step 5: Position Computation
  // ========================================
  const positions = computePositions(
    finalOrdering,
    edges,
    bidirectionalPairs,
    cycles,
    roles,
    constraints,
    fullConfig
  );

  // ========================================
  // Build Result
  // ========================================
  
  // Build cycle groups map
  const cycleGroups = new Map<string, string[]>();
  cycles.forEach((cycle, index) => {
    cycleGroups.set(`cycle-${index}`, cycle);
  });

  // Build metadata
  const metadata: LayoutMetadata = {
    entryNodes: findNodesByRole(roles, "entry"),
    exitNodes: findNodesByRole(roles, "exit"),
    orchestratorNodes: findNodesByRole(roles, "orchestrator"),
    cycleCount: cycles.length,
    crossingCount: orderingResult.crossingCount,
  };

  return {
    positions,
    layers: finalOrdering,
    cycleGroups,
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
export { analyzeGraph, findNodesByRole } from "./graphAnalysis";
export { createConstraints, createLayoutBounds, validatePositions } from "./constraints";
export { assignLayers, compactLayers } from "./layering";
export { minimizeCrossings, centerOrchestrators } from "./ordering";
export { computePositions, toReactFlowPosition, snapToGrid } from "./positioning";
