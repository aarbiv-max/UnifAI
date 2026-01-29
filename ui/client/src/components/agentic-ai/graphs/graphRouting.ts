/**
 * Smart Edge Routing for ReactFlow Graphs
 * 
 * This module provides orthogonal edge routing with A* pathfinding to create
 * clean, non-overlapping edges between nodes. It also handles bidirectional
 * edge detection and styling.
 */

import { Edge, MarkerType, Node } from "reactflow";
import { getPaletteColor } from "@/lib/colorUtils";
import { MinHeap } from "@/lib/dataStructures";

// ============================================================================
// Types
// ============================================================================

type Point = { x: number; y: number };

type NodeBox = {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  center: Point;
};

type Anchor = "auto" | "top" | "bottom";

// ============================================================================
// Constants
// ============================================================================

const GRID_SIZE = 16;           // Grid cell size for pathfinding
const NODE_PADDING = 16;        // Padding around nodes to avoid edge overlap
const ROUTE_MARGIN = 120;       // Extra margin around the graph bounds
const EDGE_BLOCK_RADIUS = 2;    // Radius to block around routed edges
const PORT_SPACING = 12;        // Spacing between multiple ports on same side
const PORT_INSET = 10;          // Minimum distance from node corner for ports
export const DEFAULT_EDGE_WIDTH = 2;
const BIDIRECTIONAL_EDGE_WIDTH = 3.5;

// ============================================================================
// Node & Connection Helpers
// ============================================================================

/** Extracts bounding box information from a ReactFlow node. */
const getNodeBox = (node: Node): NodeBox => {
  const measured = (node as { measured?: { width?: number; height?: number } }).measured;
  const width = node.width ?? measured?.width ?? 180;
  const height = node.height ?? measured?.height ?? 80;
  const center = {
    x: node.position.x + width / 2,
    y: node.position.y + height / 2,
  };
  return {
    id: node.id,
    x: node.position.x,
    y: node.position.y,
    width,
    height,
    center,
  };
};

/** Calculates the connection point on a node based on the anchor direction. */
const getConnectionPoint = (
  source: NodeBox,
  target: NodeBox,
  anchor: Anchor,
): Point => {
  if (anchor === "bottom") {
    return { x: source.center.x, y: source.y + source.height };
  }
  if (anchor === "top") {
    return { x: source.center.x, y: source.y };
  }
  // Auto: determine based on relative positions
  const dx = target.center.x - source.center.x;
  const dy = target.center.y - source.center.y;
  if (Math.abs(dx) > Math.abs(dy)) {
    return {
      x: dx > 0 ? source.x + source.width : source.x,
      y: source.center.y,
    };
  }
  return {
    x: source.center.x,
    y: dy > 0 ? source.y + source.height : source.y,
  };
};

/** Creates a unique key for a grid cell. */
const pointKey = (gx: number, gy: number) => `${gx},${gy}`;

// ============================================================================
// Main Export: buildSmartEdges
// ============================================================================

/**
 * Transforms ReactFlow edges into smart-routed edges with orthogonal paths.
 * 
 * Features:
 * - A* pathfinding to avoid node overlaps
 * - Bidirectional edge detection and merged rendering
 * - Port spreading when multiple edges connect to the same node
 * - Path compression to minimize waypoints
 */
export const buildSmartEdges = (
  nodes: Node[],
  edges: Edge[],
  primaryHex: string,
): Edge[] => {
  if (nodes.length === 0 || edges.length === 0) {
    return edges;
  }

  // --- Setup: Build node map and grid bounds ---
  const nodeBoxes = nodes.map(getNodeBox);
  const nodeBoxMap = new Map(nodeBoxes.map((node) => [node.id, node]));
  const minX = Math.min(...nodeBoxes.map((node) => node.x)) - ROUTE_MARGIN;
  const minY = Math.min(...nodeBoxes.map((node) => node.y)) - ROUTE_MARGIN;
  const maxX = Math.max(...nodeBoxes.map((node) => node.x + node.width)) + ROUTE_MARGIN;
  const maxY = Math.max(...nodeBoxes.map((node) => node.y + node.height)) + ROUTE_MARGIN;

  const cols = Math.ceil((maxX - minX) / GRID_SIZE) + 1;
  const rows = Math.ceil((maxY - minY) / GRID_SIZE) + 1;

  // Grid conversion helpers
  const toGrid = (point: Point) => ({
    gx: Math.round((point.x - minX) / GRID_SIZE),
    gy: Math.round((point.y - minY) / GRID_SIZE),
  });

  const toPoint = (gx: number, gy: number): Point => ({
    x: minX + gx * GRID_SIZE,
    y: minY + gy * GRID_SIZE,
  });

  // --- Obstacle Grid: Mark nodes as blocked ---
  const obstacles = new Set<string>();

  const blockRect = (x: number, y: number, width: number, height: number) => {
    const startX = Math.floor((x - minX) / GRID_SIZE);
    const endX = Math.ceil((x + width - minX) / GRID_SIZE);
    const startY = Math.floor((y - minY) / GRID_SIZE);
    const endY = Math.ceil((y + height - minY) / GRID_SIZE);
    for (let gx = startX; gx <= endX; gx += 1) {
      for (let gy = startY; gy <= endY; gy += 1) {
        if (gx >= 0 && gx < cols && gy >= 0 && gy < rows) {
          obstacles.add(pointKey(gx, gy));
        }
      }
    }
  };

  // Block all nodes with padding
  nodeBoxes.forEach((node) => {
    blockRect(
      node.x - NODE_PADDING,
      node.y - NODE_PADDING,
      node.width + NODE_PADDING * 2,
      node.height + NODE_PADDING * 2,
    );
  });

  /** Marks a routed path as blocked to prevent edge overlap. */
  const blockPath = (points: Point[]) => {
    if (points.length < 2) return;
    for (let i = 0; i < points.length - 1; i += 1) {
      const start = points[i];
      const end = points[i + 1];
      const segmentDx = end.x - start.x;
      const segmentDy = end.y - start.y;
      const length = Math.hypot(segmentDx, segmentDy);
      const steps = Math.max(1, Math.ceil(length / (GRID_SIZE / 2)));
      for (let step = 0; step <= steps; step += 1) {
        const t = step / steps;
        const point = { x: start.x + segmentDx * t, y: start.y + segmentDy * t };
        const { gx, gy } = toGrid(point);
        for (let offsetX = -EDGE_BLOCK_RADIUS; offsetX <= EDGE_BLOCK_RADIUS; offsetX += 1) {
          for (let offsetY = -EDGE_BLOCK_RADIUS; offsetY <= EDGE_BLOCK_RADIUS; offsetY += 1) {
            const nextGX = gx + offsetX;
            const nextGY = gy + offsetY;
            if (nextGX >= 0 && nextGX < cols && nextGY >= 0 && nextGY < rows) {
              obstacles.add(pointKey(nextGX, nextGY));
            }
          }
        }
      }
    }
  };

  // --- A* Pathfinding ---
  const findPath = (
    start: Point,
    goal: Point,
    allowStartKey: string,
    allowGoalKey: string,
  ) => {
    const startCell = toGrid(start);
    const goalCell = toGrid(goal);
    const startKey = pointKey(startCell.gx, startCell.gy);
    const goalKey = pointKey(goalCell.gx, goalCell.gy);

    const openSet = new Set<string>([startKey]);
    const openHeap = new MinHeap();
    const cameFrom = new Map<string, string>();
    const gScore = new Map<string, number>([[startKey, 0]]);
    const fScore = new Map<string, number>([
      [startKey, Math.abs(startCell.gx - goalCell.gx) + Math.abs(startCell.gy - goalCell.gy)],
    ]);
    openHeap.push({ key: startKey, score: fScore.get(startKey) ?? 0 });

    const neighbors = [
      { dx: 1, dy: 0 },
      { dx: -1, dy: 0 },
      { dx: 0, dy: 1 },
      { dx: 0, dy: -1 },
    ];

    const isBlocked = (gx: number, gy: number) => {
      const key = pointKey(gx, gy);
      if (key === allowStartKey || key === allowGoalKey) return false;
      return obstacles.has(key);
    };

    while (openSet.size > 0 && openHeap.size > 0) {
      const current = openHeap.pop();
      if (!current) break;
      const currentKey = current.key;
      if (!openSet.has(currentKey)) continue;
      const currentScore = fScore.get(currentKey);
      if (currentScore !== undefined && current.score !== currentScore) continue;

      if (currentKey === goalKey) {
        // Reconstruct path
        const path: Point[] = [];
        let cursorKey: string | undefined = currentKey;
        while (cursorKey) {
          const [gx, gy] = cursorKey.split(",").map(Number);
          path.push(toPoint(gx, gy));
          cursorKey = cameFrom.get(cursorKey);
        }
        return path.reverse();
      }

      openSet.delete(currentKey);
      const [currentX, currentY] = currentKey.split(",").map(Number);

      neighbors.forEach(({ dx, dy }) => {
        const neighborX = currentX + dx;
        const neighborY = currentY + dy;
        if (neighborX < 0 || neighborX >= cols || neighborY < 0 || neighborY >= rows) return;
        if (isBlocked(neighborX, neighborY)) return;

        const neighborKey = pointKey(neighborX, neighborY);
        const tentativeG = (gScore.get(currentKey) ?? 0) + 1;
        if (tentativeG < (gScore.get(neighborKey) ?? Number.POSITIVE_INFINITY)) {
          cameFrom.set(neighborKey, currentKey);
          gScore.set(neighborKey, tentativeG);
          const heuristic = Math.abs(neighborX - goalCell.gx) + Math.abs(neighborY - goalCell.gy);
          const nextScore = tentativeG + heuristic;
          fScore.set(neighborKey, nextScore);
          openSet.add(neighborKey);
          openHeap.push({ key: neighborKey, score: nextScore });
        }
      });
    }

    return [];
  };

  /** Removes redundant collinear points from a path. */
  const compressPoints = (points: Point[]) => {
    if (points.length < 3) return points;
    const result: Point[] = [points[0]];
    for (let i = 1; i < points.length - 1; i += 1) {
      const prev = result[result.length - 1];
      const current = points[i];
      const next = points[i + 1];
      const isCollinear =
        (prev.x === current.x && current.x === next.x) ||
        (prev.y === current.y && current.y === next.y);
      if (!isCollinear) {
        result.push(current);
      }
    }
    result.push(points[points.length - 1]);
    return result;
  };

  // --- Bidirectional Edge Detection ---
  const routedPointsByEdge = new Map<string, Point[]>();
  const edgeKey = (source: string, target: string) => `${source}::${target}`;
  const edgeKeys = new Set(edges.map((edge) => edgeKey(edge.source, edge.target)));
  const isBidirectional = (edge: Edge) => edgeKeys.has(edgeKey(edge.target, edge.source));
  const isBidirectionalPrimary = (edge: Edge) =>
    isBidirectional(edge) && edge.source.localeCompare(edge.target) <= 0;

  // --- Edge Styling ---
  const defaultStroke = primaryHex;
  const bidirectionalStroke = getPaletteColor(primaryHex, 1, 4);
  const pairKey = (source: string, target: string) =>
    source < target ? `${source}::${target}` : `${target}::${source}`;
  const bidirectionalPairs = new Map<string, string[]>();
  edges.forEach((edge) => {
    if (edgeKeys.has(edgeKey(edge.target, edge.source))) {
      const key = pairKey(edge.source, edge.target);
      const existing = bidirectionalPairs.get(key) || [];
      bidirectionalPairs.set(key, [...existing, edge.id]);
    }
  });

  // --- Port Spreading: Handle multiple edges on same node ---
  const sortedEdges = [...edges].sort((a, b) => {
    const sourceA = nodeBoxMap.get(a.source);
    const targetA = nodeBoxMap.get(a.target);
    const sourceB = nodeBoxMap.get(b.source);
    const targetB = nodeBoxMap.get(b.target);
    if (!sourceA || !targetA || !sourceB || !targetB) return 0;
    const distA = Math.hypot(sourceA.center.x - targetA.center.x, sourceA.center.y - targetA.center.y);
    const distB = Math.hypot(sourceB.center.x - targetB.center.x, sourceB.center.y - targetB.center.y);
    return distB - distA;
  });

  const outgoingBySource = new Map<string, Edge[]>();
  const incomingByTarget = new Map<string, Edge[]>();
  sortedEdges.forEach((edge) => {
    const sourceList = outgoingBySource.get(edge.source) || [];
    sourceList.push(edge);
    outgoingBySource.set(edge.source, sourceList);
    const targetList = incomingByTarget.get(edge.target) || [];
    targetList.push(edge);
    incomingByTarget.set(edge.target, targetList);
  });

  const sortEdgesByPosition = (edgesToSort: Edge[], useTarget: boolean) => {
    edgesToSort.sort((a, b) => {
      const nodeA = nodeBoxMap.get(useTarget ? a.target : a.source);
      const nodeB = nodeBoxMap.get(useTarget ? b.target : b.source);
      if (!nodeA || !nodeB) return 0;
      return nodeA.center.x - nodeB.center.x;
    });
  };

  outgoingBySource.forEach((edgeList) => sortEdgesByPosition(edgeList, true));
  incomingByTarget.forEach((edgeList) => sortEdgesByPosition(edgeList, false));

  /** Calculates horizontal offset for ports when multiple edges connect to same node side. */
  const getPortOffset = (node: NodeBox, edge: Edge, anchor: Anchor, isSource: boolean): Point => {
    const list = isSource ? outgoingBySource.get(node.id) || [] : incomingByTarget.get(node.id) || [];
    const total = list.length;
    if (total <= 1) return { x: 0, y: 0 };

    const index = Math.max(0, list.findIndex((item) => item.id === edge.id));
    const mid = (total - 1) / 2;
    const offset = (index - mid) * PORT_SPACING;

    if (anchor === "top" || anchor === "bottom") {
      const maxOffset = Math.max(0, node.width / 2 - PORT_INSET);
      return { x: Math.max(-maxOffset, Math.min(maxOffset, offset)), y: 0 };
    }
    const maxOffset = Math.max(0, node.height / 2 - PORT_INSET);
    return { x: 0, y: Math.max(-maxOffset, Math.min(maxOffset, offset)) };
  };

  // --- Route Each Edge ---
  sortedEdges.forEach((edge) => {
    // Skip non-primary bidirectional edges (they share the primary edge's path)
    if (isBidirectional(edge) && !isBidirectionalPrimary(edge)) return;

    const sourceNode = nodeBoxMap.get(edge.source);
    const targetNode = nodeBoxMap.get(edge.target);
    if (!sourceNode || !targetNode) return;

    // Determine anchor points based on relative node positions
    const verticalGap = targetNode.center.y - sourceNode.center.y;
    const horizontalGap = targetNode.center.x - sourceNode.center.x;
    let sourceAnchor: Anchor = "auto";
    let targetAnchor: Anchor = "auto";
    if (Math.abs(verticalGap) >= Math.abs(horizontalGap)) {
      if (verticalGap >= 0) {
        sourceAnchor = "bottom";
        targetAnchor = "top";
      } else {
        sourceAnchor = "top";
        targetAnchor = "bottom";
      }
    }

    // Calculate start and end points with port offsets
    const baseStart = getConnectionPoint(sourceNode, targetNode, sourceAnchor);
    const baseEnd = getConnectionPoint(targetNode, sourceNode, targetAnchor);
    const startOffset = getPortOffset(sourceNode, edge, sourceAnchor, true);
    const endOffset = getPortOffset(targetNode, edge, targetAnchor, false);
    const startPoint = { x: baseStart.x + startOffset.x, y: baseStart.y + startOffset.y };
    const endPoint = { x: baseEnd.x + endOffset.x, y: baseEnd.y + endOffset.y };

    // Find path and store
    const { gx: startGX, gy: startGY } = toGrid(startPoint);
    const { gx: goalGX, gy: goalGY } = toGrid(endPoint);
    const startKey = pointKey(startGX, startGY);
    const goalKey = pointKey(goalGX, goalGY);

    const path = findPath(startPoint, endPoint, startKey, goalKey);
    let points = path.length > 0 ? path : [startPoint, endPoint];
    points[0] = startPoint;
    points[points.length - 1] = endPoint;
    points = compressPoints(points);
    routedPointsByEdge.set(edge.id, points);
    blockPath(points);
  });

  // --- Build Output Edges ---
  const output: Edge[] = [];
  edges.forEach((edge) => {
    const bidirectional = isBidirectional(edge);
    if (bidirectional && !isBidirectionalPrimary(edge)) return;

    const routedPoints = routedPointsByEdge.get(edge.id);
    if (!routedPoints) {
      output.push(edge);
      return;
    }

    const stroke = bidirectional ? bidirectionalStroke : defaultStroke;
    const strokeWidth = bidirectional ? BIDIRECTIONAL_EDGE_WIDTH : DEFAULT_EDGE_WIDTH;
    const label = edge.data?.label;
    const pairIds = bidirectional ? bidirectionalPairs.get(pairKey(edge.source, edge.target)) : undefined;
    const arrowSize = bidirectional ? 18 : 16;

    output.push({
      ...edge,
      type: "routed",
      style: { ...(edge.style || {}), stroke, strokeWidth },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: arrowSize,
        height: arrowSize,
        color: stroke,
      },
      markerStart: bidirectional
        ? { type: MarkerType.ArrowClosed, width: arrowSize, height: arrowSize, color: stroke }
        : undefined,
      data: {
        ...edge.data,
        routedPoints,
        label,
        isBidirectional: bidirectional,
        bidirectionalEdgeIds: pairIds && pairIds.length > 1 ? pairIds : undefined,
      },
    });
  });

  return output;
};
