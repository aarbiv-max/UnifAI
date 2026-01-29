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
  StarGroup,
  DepthGroup,
  NodeDepthInfo,
  DepthAnalysis,
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
        if (typeof targetNodeId === "string" && nodeIds.has(targetNodeId)) {
          const edgeKey = `${item.uid}::${targetNodeId}`;
          if (!edgeSet.has(edgeKey)) {
            edgeSet.add(edgeKey);
            edges.push({
              source: item.uid,
              target: targetNodeId,
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
// Star / Hub-and-Spoke Detection
// ============================================================================

/** Minimum number of bidirectional neighbors for a node to be considered a hub */
const MIN_SPOKES_FOR_STAR = 3;

/**
 * Detects star (hub-and-spoke) patterns in the graph
 * 
 * A star is identified when:
 * - A hub node has ≥3 bidirectional neighbors
 * - All neighbors are in the semantic middle band (not entry/exit)
 * - The hub is typically an orchestrator but can be any central node
 * 
 * @param nodes - Map of node IDs to node info
 * @param edges - All edges in the graph
 * @param bidirectionalPairs - Set of bidirectional edge keys
 * @param roles - Map of node IDs to their semantic roles
 * @returns Array of detected star groups
 */
export function detectStarGroups(
  nodes: Map<string, NodeInfo>,
  edges: LayoutEdge[],
  bidirectionalPairs: Set<string>,
  roles: Map<string, NodeRole>
): StarGroup[] {
  const starGroups: StarGroup[] = [];
  const usedAsSpoke = new Set<string>();

  // Build bidirectional neighbor map
  const bidirectionalNeighbors = new Map<string, string[]>();
  nodes.forEach((_, nodeId) => {
    bidirectionalNeighbors.set(nodeId, []);
  });

  edges.forEach((edge) => {
    const edgeKey = `${edge.source}::${edge.target}`;
    if (bidirectionalPairs.has(edgeKey)) {
      // Add to both directions
      bidirectionalNeighbors.get(edge.source)?.push(edge.target);
    }
  });

  // Find potential hubs (nodes with ≥3 bidirectional neighbors)
  // Prioritize orchestrators, then by neighbor count
  const potentialHubs: Array<{ nodeId: string; neighbors: string[]; isOrchestrator: boolean }> = [];

  nodes.forEach((_, nodeId) => {
    const role = roles.get(nodeId);
    
    // Skip entry/exit nodes - they can't be hubs
    if (role === "entry" || role === "exit") return;

    const neighbors = bidirectionalNeighbors.get(nodeId) || [];
    
    // Filter to only include neighbors that are in the middle band (not entry/exit)
    const eligibleNeighbors = neighbors.filter((neighborId) => {
      const neighborRole = roles.get(neighborId);
      return neighborRole !== "entry" && neighborRole !== "exit";
    });

    if (eligibleNeighbors.length >= MIN_SPOKES_FOR_STAR) {
      potentialHubs.push({
        nodeId,
        neighbors: eligibleNeighbors,
        isOrchestrator: role === "orchestrator",
      });
    }
  });

  // Sort: orchestrators first, then by neighbor count (descending)
  potentialHubs.sort((a, b) => {
    if (a.isOrchestrator !== b.isOrchestrator) {
      return a.isOrchestrator ? -1 : 1;
    }
    return b.neighbors.length - a.neighbors.length;
  });

  // Create star groups, avoiding overlapping spokes
  potentialHubs.forEach(({ nodeId, neighbors }) => {
    // Skip if this node is already used as a spoke in another star
    if (usedAsSpoke.has(nodeId)) return;

    // Filter out neighbors already used as spokes
    const availableSpokes = neighbors.filter((n) => !usedAsSpoke.has(n));

    // Need at least MIN_SPOKES_FOR_STAR available spokes
    if (availableSpokes.length >= MIN_SPOKES_FOR_STAR) {
      const starGroup: StarGroup = {
        id: `star-${starGroups.length}`,
        hubId: nodeId,
        spokeIds: availableSpokes,
        spokeCount: availableSpokes.length,
      };

      starGroups.push(starGroup);

      // Mark spokes as used
      availableSpokes.forEach((spokeId) => { usedAsSpoke.add(spokeId); });
    }
  });

  return starGroups;
}

/**
 * Checks if a node is part of any star group (as hub or spoke)
 */
export function isInStarGroup(
  nodeId: string,
  starGroups: StarGroup[]
): boolean {
  return starGroups.some(
    (group) => group.hubId === nodeId || group.spokeIds.includes(nodeId)
  );
}

/**
 * Gets the star group a node belongs to (if any)
 */
export function getStarGroupForNode(
  nodeId: string,
  starGroups: StarGroup[]
): StarGroup | undefined {
  return starGroups.find(
    (group) => group.hubId === nodeId || group.spokeIds.includes(nodeId)
  );
}

/**
 * Checks if a node is a hub in any star group
 */
export function isStarHub(
  nodeId: string,
  starGroups: StarGroup[]
): boolean {
  return starGroups.some((group) => group.hubId === nodeId);
}

/**
 * Checks if a node is a spoke in any star group
 */
export function isStarSpoke(
  nodeId: string,
  starGroups: StarGroup[]
): boolean {
  return starGroups.some((group) => group.spokeIds.includes(nodeId));
}

// ============================================================================
// Depth Analysis (Relative Position to Orchestrator/Hub)
// ============================================================================

/**
 * Computes shortest directed distances from a source node to all other nodes using BFS
 * 
 * @param sourceId - The starting node
 * @param adjacency - Adjacency list (outgoing edges)
 * @returns Map of node ID to shortest distance (-1 if unreachable)
 */
function computeShortestDistances(
  sourceId: string,
  adjacency: Map<string, string[]>
): Map<string, number> {
  const distances = new Map<string, number>();
  
  // Initialize all distances to -1 (unreachable)
  adjacency.forEach((_, nodeId) => {
    distances.set(nodeId, -1);
  });
  
  // BFS from source
  const queue: Array<{ nodeId: string; distance: number }> = [];
  queue.push({ nodeId: sourceId, distance: 0 });
  distances.set(sourceId, 0);
  
  while (queue.length > 0) {
    const { nodeId, distance } = queue.shift()!;
    const neighbors = adjacency.get(nodeId) || [];
    
    for (const neighbor of neighbors) {
      if (distances.get(neighbor) === -1) {
        distances.set(neighbor, distance + 1);
        queue.push({ nodeId: neighbor, distance: distance + 1 });
      }
    }
  }
  
  return distances;
}

/**
 * Computes the depth analysis for all nodes relative to orchestrator/hub nodes
 * 
 * This function:
 * 1. Identifies orchestrator/hub nodes
 * 2. Computes shortest paths TO and FROM each hub
 * 3. Classifies each node into a depth group based on reachability
 * 
 * Classification rules:
 * - HUB: The orchestrator node itself
 * - PINNED_TOP: Entry nodes (user_question)
 * - PINNED_BOTTOM: Exit nodes (final_answer)
 * - UPSTREAM: Can reach hub, but hub cannot reach this node
 * - DOWNSTREAM: Hub can reach this node, but node cannot reach hub
 * - CYCLIC: Both directions exist (bidirectional relationship)
 * - ISOLATED: No path to or from hub
 * 
 * @param nodes - Map of node IDs to node info
 * @param edges - All edges in the graph
 * @param roles - Map of node IDs to semantic roles
 * @returns Complete depth analysis
 */
export function computeDepthAnalysis(
  nodes: Map<string, NodeInfo>,
  edges: LayoutEdge[],
  roles: Map<string, NodeRole>
): DepthAnalysis {
  // Build forward and reverse adjacency lists
  const forwardAdj = new Map<string, string[]>();
  const reverseAdj = new Map<string, string[]>();
  
  nodes.forEach((_, nodeId) => {
    forwardAdj.set(nodeId, []);
    reverseAdj.set(nodeId, []);
  });
  
  edges.forEach((edge) => {
    forwardAdj.get(edge.source)?.push(edge.target);
    reverseAdj.get(edge.target)?.push(edge.source);
  });
  
  // Identify hub nodes (orchestrators, or nodes with highest connectivity if none)
  const hubNodes: string[] = [];
  roles.forEach((role, nodeId) => {
    if (role === "orchestrator") {
      hubNodes.push(nodeId);
    }
  });
  
  // If no orchestrator found, find the node with highest bidirectional connectivity
  if (hubNodes.length === 0) {
    let maxConnectivity = 0;
    let bestHub = "";
    
    nodes.forEach((_, nodeId) => {
      const role = roles.get(nodeId);
      // Skip entry/exit nodes as potential hubs
      if (role === "entry" || role === "exit") return;
      
      const outDegree = forwardAdj.get(nodeId)?.length || 0;
      const inDegree = reverseAdj.get(nodeId)?.length || 0;
      const connectivity = outDegree + inDegree;
      
      if (connectivity > maxConnectivity) {
        maxConnectivity = connectivity;
        bestHub = nodeId;
      }
    });
    
    if (bestHub) {
      hubNodes.push(bestHub);
    }
  }
  
  // Compute distances from each hub
  // For multi-hub graphs, we use the minimum distance to any hub
  const distancesToHub = new Map<string, number>();
  const distancesFromHub = new Map<string, number>();
  
  nodes.forEach((_, nodeId) => {
    distancesToHub.set(nodeId, -1);
    distancesFromHub.set(nodeId, -1);
  });
  
  hubNodes.forEach((hubId) => {
    // Distance FROM hub (forward BFS)
    const fromHub = computeShortestDistances(hubId, forwardAdj);
    
    // Distance TO hub (reverse BFS = forward BFS on reverse graph)
    const toHub = computeShortestDistances(hubId, reverseAdj);
    
    // Merge with minimum distances
    fromHub.forEach((dist, nodeId) => {
      const current = distancesFromHub.get(nodeId) || -1;
      if (dist !== -1 && (current === -1 || dist < current)) {
        distancesFromHub.set(nodeId, dist);
      }
    });
    
    toHub.forEach((dist, nodeId) => {
      const current = distancesToHub.get(nodeId) || -1;
      if (dist !== -1 && (current === -1 || dist < current)) {
        distancesToHub.set(nodeId, dist);
      }
    });
  });
  
  // Classify each node into a depth group
  const nodeDepths = new Map<string, NodeDepthInfo>();
  const groupedNodes = new Map<DepthGroup, string[]>();
  
  // Initialize grouped nodes
  const allGroups: DepthGroup[] = [
    "UPSTREAM", "DOWNSTREAM", "CYCLIC", "ISOLATED", "HUB", "PINNED_TOP", "PINNED_BOTTOM"
  ];
  allGroups.forEach((group) => {
    groupedNodes.set(group, []);
  });
  
  nodes.forEach((_, nodeId) => {
    const role = roles.get(nodeId);
    const toHub = distancesToHub.get(nodeId) ?? -1;
    const fromHub = distancesFromHub.get(nodeId) ?? -1;
    
    let depthGroup: DepthGroup;
    let semanticDepth: number;
    
    // Priority: Pinned nodes first, then hub, then relative position
    if (role === "entry") {
      depthGroup = "PINNED_TOP";
      semanticDepth = -1000; // Always at top
    } else if (role === "exit") {
      depthGroup = "PINNED_BOTTOM";
      semanticDepth = 1000; // Always at bottom
    } else if (hubNodes.includes(nodeId)) {
      depthGroup = "HUB";
      semanticDepth = 0; // Hub is the reference point
    } else if (toHub !== -1 && fromHub !== -1) {
      // Bidirectional - cyclic relationship with hub
      depthGroup = "CYCLIC";
      // Semantic depth is based on average distance (closer = more central)
      semanticDepth = (toHub + fromHub) / 2;
    } else if (toHub !== -1 && fromHub === -1) {
      // Can only reach hub = UPSTREAM (before hub in flow)
      depthGroup = "UPSTREAM";
      // Negative depth = above hub, magnitude = distance
      semanticDepth = -toHub;
    } else if (fromHub !== -1 && toHub === -1) {
      // Hub can only reach this = DOWNSTREAM (after hub in flow)
      depthGroup = "DOWNSTREAM";
      // Positive depth = below hub, magnitude = distance
      semanticDepth = fromHub;
    } else {
      // No connection to hub
      depthGroup = "ISOLATED";
      semanticDepth = 0;
    }
    
    const depthInfo: NodeDepthInfo = {
      nodeId,
      depthGroup,
      distanceToOrchestrator: toHub,
      distanceFromOrchestrator: fromHub,
      semanticDepth,
    };
    
    nodeDepths.set(nodeId, depthInfo);
    groupedNodes.get(depthGroup)?.push(nodeId);
  });
  
  return {
    nodeDepths,
    groupedNodes,
    hubNodes,
    isMultiHub: hubNodes.length > 1,
  };
}

/**
 * Gets the depth group for a specific node
 */
export function getNodeDepthGroup(
  nodeId: string,
  depthAnalysis: DepthAnalysis
): DepthGroup {
  return depthAnalysis.nodeDepths.get(nodeId)?.depthGroup || "ISOLATED";
}

/**
 * Gets the semantic depth value for a specific node
 * Lower values = higher in the graph (upstream)
 * Higher values = lower in the graph (downstream)
 */
export function getSemanticDepth(
  nodeId: string,
  depthAnalysis: DepthAnalysis
): number {
  return depthAnalysis.nodeDepths.get(nodeId)?.semanticDepth || 0;
}

/**
 * Checks if two nodes are in compatible depth groups for same-layer placement
 * Nodes in different semantic bands should generally not share the same layer
 */
export function areDepthGroupsCompatible(
  groupA: DepthGroup,
  groupB: DepthGroup
): boolean {
  // Same group is always compatible
  if (groupA === groupB) return true;
  
  // CYCLIC can coexist with HUB (they're at similar vertical positions)
  if ((groupA === "CYCLIC" && groupB === "HUB") || 
      (groupA === "HUB" && groupB === "CYCLIC")) {
    return true;
  }
  
  // ISOLATED nodes are flexible
  if (groupA === "ISOLATED" || groupB === "ISOLATED") {
    return true;
  }
  
  // UPSTREAM and DOWNSTREAM should NOT share layers
  if ((groupA === "UPSTREAM" && groupB === "DOWNSTREAM") ||
      (groupA === "DOWNSTREAM" && groupB === "UPSTREAM")) {
    return false;
  }
  
  // PINNED nodes are special - they should not mix with others
  if (groupA === "PINNED_TOP" || groupA === "PINNED_BOTTOM" ||
      groupB === "PINNED_TOP" || groupB === "PINNED_BOTTOM") {
    return false;
  }
  
  return true;
}

// ============================================================================
// Main Analysis Function
// ============================================================================

/**
 * Options for graph analysis
 */
export interface AnalyzeGraphOptions {
  /** 
   * Whether to compute depth analysis for semantic grouping.
   * Set to false for simple graphs or when performance is critical.
   * @default true
   */
  enableDepthAnalysis?: boolean;
}

/**
 * Creates an empty depth analysis result (used when depth analysis is skipped)
 */
function createEmptyDepthAnalysis(): DepthAnalysis {
  return {
    nodeDepths: new Map(),
    groupedNodes: new Map([
      ["UPSTREAM", []],
      ["DOWNSTREAM", []],
      ["CYCLIC", []],
      ["ISOLATED", []],
      ["HUB", []],
      ["PINNED_TOP", []],
      ["PINNED_BOTTOM", []],
    ]),
    hubNodes: [],
    isMultiHub: false,
  };
}

/**
 * Analyzes the complete graph structure from plan items and node definitions
 * This is the main entry point for graph analysis
 * 
 * @param plan - Array of plan items defining the graph
 * @param nodeMap - Map of node RIDs to definitions
 * @param options - Analysis options (e.g., enable/disable depth analysis)
 */
export function analyzeGraph(
  plan: PlanItem[],
  nodeMap: Record<string, NodeDefinition>,
  options: AnalyzeGraphOptions = {}
): GraphStructure {
  const { enableDepthAnalysis = true } = options;

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

  // Detect star/hub-and-spoke patterns
  const starGroups = detectStarGroups(nodes, edges, bidirectionalPairs, roles);

  // Compute depth analysis relative to orchestrator/hub (optional)
  // This is skipped for simple graphs or when performance is critical
  const depthAnalysis = enableDepthAnalysis 
    ? computeDepthAnalysis(nodes, edges, roles)
    : createEmptyDepthAnalysis();

  return {
    nodes,
    edges,
    bidirectionalPairs,
    cycles,
    roles,
    starGroups,
    depthAnalysis,
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
