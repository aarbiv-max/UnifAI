/**
 * Graph Analysis Module
 * 
 * Responsible for:
 * - Edge extraction from plan items
 * - Node role classification
 * - Strongly Connected Component (SCC) detection using Tarjan's algorithm
 */

import {
  PlanItem,
  NodeDefinition,
  NodeRole,
  NodeInfo,
  LayoutEdge,
  GraphStructure,
} from "./types";

// ============================================================================
// Edge Extraction
// ============================================================================

/**
 * Extracts all edges from the plan items
 * Handles both 'after' relationships and 'branches'
 */
export function extractEdges(
  plan: PlanItem[],
  nodeIds: Set<string>
): { edges: LayoutEdge[]; bidirectionalPairs: Set<string> } {
  const edges: LayoutEdge[] = [];
  const edgeSet = new Set<string>();
  const bidirectionalPairs = new Set<string>();

  // First pass: collect all edges
  plan.forEach((item) => {
    // Handle 'after' relationships (incoming edges)
    if (item.after) {
      const predecessors = Array.isArray(item.after) ? item.after : [item.after];
      predecessors.forEach((predecessorId) => {
        if (predecessorId && nodeIds.has(predecessorId)) {
          const edgeKey = `${predecessorId}::${item.uid}`;
          if (!edgeSet.has(edgeKey)) {
            edgeSet.add(edgeKey);
            edges.push({
              source: predecessorId,
              target: item.uid,
              isBidirectional: false,
              isBranch: false,
            });
          }
        }
      });
    }

    // Handle 'branches' (outgoing conditional edges)
    if (item.branches) {
      Object.entries(item.branches).forEach(([, targetNodeId]) => {
        if (targetNodeId && nodeIds.has(targetNodeId as string)) {
          const edgeKey = `${item.uid}::${targetNodeId}`;
          if (!edgeSet.has(edgeKey)) {
            edgeSet.add(edgeKey);
            edges.push({
              source: item.uid,
              target: targetNodeId as string,
              isBidirectional: false,
              isBranch: true,
            });
          }
        }
      });
    }
  });

  // Second pass: identify bidirectional edges
  edges.forEach((edge) => {
    const reverseKey = `${edge.target}::${edge.source}`;
    if (edgeSet.has(reverseKey)) {
      const edgeKey = `${edge.source}::${edge.target}`;
      bidirectionalPairs.add(edgeKey);
      bidirectionalPairs.add(reverseKey);
      edge.isBidirectional = true;
    }
  });

  return { edges, bidirectionalPairs };
}

// ============================================================================
// Role Classification
// ============================================================================

/**
 * Classifies a single node's role based on its type
 */
function classifyNodeType(nodeType: string): NodeRole {
  switch (nodeType) {
    case "user_question_node":
      return "entry";
    case "final_answer_node":
      return "exit";
    case "orchestrator_node":
      return "orchestrator";
    case "router_direct":
      return "control";
    default:
      if (nodeType.includes("router") || nodeType.includes("condition")) {
        return "control";
      }
      return "agent";
  }
}

/**
 * Classifies all nodes by their semantic role
 */
export function classifyNodeRoles(
  nodes: Map<string, NodeInfo>
): Map<string, NodeRole> {
  const roles = new Map<string, NodeRole>();

  nodes.forEach(({ type }, nodeId) => {
    roles.set(nodeId, classifyNodeType(type));
  });

  return roles;
}

// ============================================================================
// SCC Detection (Tarjan's Algorithm)
// ============================================================================

interface TarjanState {
  index: number;
  indices: Map<string, number>;
  lowlinks: Map<string, number>;
  onStack: Set<string>;
  stack: string[];
  sccs: string[][];
}

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

// ============================================================================
// Main Analysis Function
// ============================================================================

/**
 * Analyzes the complete graph structure from plan items and node definitions
 * This is the main entry point for graph analysis
 */
export function analyzeGraph(
  plan: PlanItem[],
  nodeMap: Record<string, NodeDefinition>
): GraphStructure {
  // Build nodes map
  const nodes = new Map<string, NodeInfo>();
  const nodeIds = new Set<string>();

  plan.forEach((item) => {
    const nodeDefinition = nodeMap[item.node];
    const nodeType = nodeDefinition?.type || "custom_agent_node";
    const nodeLabel = nodeDefinition?.name || item.meta?.display_name || item.uid;
    
    nodes.set(item.uid, { type: nodeType, label: nodeLabel });
    nodeIds.add(item.uid);
  });

  // Extract edges
  const { edges, bidirectionalPairs } = extractEdges(plan, nodeIds);

  // Classify roles
  const roles = classifyNodeRoles(nodes);

  // Detect cycles
  const cycles = detectCycles(nodes, edges);

  return {
    nodes,
    edges,
    bidirectionalPairs,
    cycles,
    roles,
  };
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Finds all nodes with a specific role
 */
export function findNodesByRole(
  roles: Map<string, NodeRole>,
  targetRole: NodeRole
): string[] {
  const result: string[] = [];
  roles.forEach((role, nodeId) => {
    if (role === targetRole) {
      result.push(nodeId);
    }
  });
  return result;
}

/**
 * Gets adjacency lists for the graph
 */
export function buildAdjacencyLists(
  nodes: Map<string, NodeInfo>,
  edges: LayoutEdge[]
): { incoming: Map<string, string[]>; outgoing: Map<string, string[]> } {
  const incoming = new Map<string, string[]>();
  const outgoing = new Map<string, string[]>();

  nodes.forEach((_, nodeId) => {
    incoming.set(nodeId, []);
    outgoing.set(nodeId, []);
  });

  edges.forEach((edge) => {
    outgoing.get(edge.source)?.push(edge.target);
    incoming.get(edge.target)?.push(edge.source);
  });

  return { incoming, outgoing };
}
