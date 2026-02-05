/**
 * Tarjan's Strongly Connected Components (SCC) Algorithm
 *
 * This module implements Tarjan's algorithm for detecting cycles (SCCs) in directed graphs.
 * Separated from graphAnalysis.ts for better code organization.
 */

import { NodeInfo, LayoutEdge } from "./types";

// ============================================================================
// Types
// ============================================================================

interface TarjanState {
  index: number;
  indices: Map<string, number>;
  lowlinks: Map<string, number>;
  onStack: Set<string>;
  stack: string[];
  sccs: string[][];
}

// ============================================================================
// Algorithm Implementation
// ============================================================================

/**
 * Recursive function for Tarjan's SCC algorithm
 */
function strongConnect(
  v: string,
  adjacency: Map<string, string[]>,
  state: TarjanState
): void {
  state.indices.set(v, state.index);
  state.lowlinks.set(v, state.index);
  state.index++;
  state.stack.push(v);
  state.onStack.add(v);

  const neighbors = adjacency.get(v) || [];
  for (const w of neighbors) {
    if (!state.indices.has(w)) {
      // Successor w has not yet been visited
      strongConnect(w, adjacency, state);
      state.lowlinks.set(
        v,
        Math.min(state.lowlinks.get(v)!, state.lowlinks.get(w)!)
      );
    } else if (state.onStack.has(w)) {
      // Successor w is on the stack (part of current SCC)
      state.lowlinks.set(
        v,
        Math.min(state.lowlinks.get(v)!, state.indices.get(w)!)
      );
    }
  }

  // If v is a root node, pop the stack and generate an SCC
  if (state.lowlinks.get(v) === state.indices.get(v)) {
    const scc: string[] = [];
    let w: string;
    do {
      w = state.stack.pop()!;
      state.onStack.delete(w);
      scc.push(w);
    } while (w !== v);
    state.sccs.push(scc);
  }
}

/**
 * Detects all strongly connected components (cycles) in the graph
 * Returns only SCCs with more than 1 node (actual cycles)
 */
export function detectCycles(
  nodes: Map<string, NodeInfo>,
  edges: LayoutEdge[]
): string[][] {
  // Build adjacency list
  const adjacency = new Map<string, string[]>();
  nodes.forEach((_, nodeId) => {
    adjacency.set(nodeId, []);
  });

  edges.forEach((edge) => {
    const neighbors = adjacency.get(edge.source);
    if (neighbors) {
      neighbors.push(edge.target);
    }
  });

  // Run Tarjan's algorithm
  const state: TarjanState = {
    index: 0,
    indices: new Map(),
    lowlinks: new Map(),
    onStack: new Set(),
    stack: [],
    sccs: [],
  };

  nodes.forEach((_, nodeId) => {
    if (!state.indices.has(nodeId)) {
      strongConnect(nodeId, adjacency, state);
    }
  });

  // Filter to only return SCCs with more than 1 node (actual cycles)
  return state.sccs.filter((scc) => scc.length > 1);
}
