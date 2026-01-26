import { Edge, MarkerType, Node } from "reactflow";
import { getPaletteColor } from "@/lib/colorUtils";

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

const GRID_SIZE = 20;
const NODE_PADDING = 16;
const ROUTE_MARGIN = 120;
export const DEFAULT_EDGE_WIDTH = 2;
const BIDIRECTIONAL_EDGE_WIDTH = 3.5;

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

const getConnectionPoint = (
  source: NodeBox,
  target: NodeBox,
  anchor: Anchor,
): Point => {
  if (anchor === "bottom") {
    return {
      x: source.center.x,
      y: source.y + source.height,
    };
  }
  if (anchor === "top") {
    return {
      x: source.center.x,
      y: source.y,
    };
  }
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

const pointKey = (gx: number, gy: number) => `${gx},${gy}`;

export const buildSmartEdges = (
  nodes: Node[],
  edges: Edge[],
  primaryHex: string,
): Edge[] => {
  if (nodes.length === 0 || edges.length === 0) {
    return edges;
  }

  const nodeBoxes = nodes.map(getNodeBox);
  const nodeBoxMap = new Map(nodeBoxes.map((node) => [node.id, node]));
  const minX = Math.min(...nodeBoxes.map((node) => node.x)) - ROUTE_MARGIN;
  const minY = Math.min(...nodeBoxes.map((node) => node.y)) - ROUTE_MARGIN;
  const maxX =
    Math.max(...nodeBoxes.map((node) => node.x + node.width)) + ROUTE_MARGIN;
  const maxY =
    Math.max(...nodeBoxes.map((node) => node.y + node.height)) + ROUTE_MARGIN;

  const cols = Math.ceil((maxX - minX) / GRID_SIZE) + 1;
  const rows = Math.ceil((maxY - minY) / GRID_SIZE) + 1;

  const toGrid = (point: Point) => ({
    gx: Math.round((point.x - minX) / GRID_SIZE),
    gy: Math.round((point.y - minY) / GRID_SIZE),
  });

  const toPoint = (gx: number, gy: number): Point => ({
    x: minX + gx * GRID_SIZE,
    y: minY + gy * GRID_SIZE,
  });

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

  nodeBoxes.forEach((node) => {
    blockRect(
      node.x - NODE_PADDING,
      node.y - NODE_PADDING,
      node.width + NODE_PADDING * 2,
      node.height + NODE_PADDING * 2,
    );
  });

  const blockPath = (points: Point[]) => {
    if (points.length < 2) return;
    for (let i = 0; i < points.length - 1; i += 1) {
      const start = points[i];
      const end = points[i + 1];
      const dx = end.x - start.x;
      const dy = end.y - start.y;
      const length = Math.hypot(dx, dy);
      const steps = Math.max(1, Math.ceil(length / (GRID_SIZE / 2)));
      for (let step = 0; step <= steps; step += 1) {
        const t = step / steps;
        const point = { x: start.x + dx * t, y: start.y + dy * t };
        const { gx, gy } = toGrid(point);
        if (gx >= 0 && gx < cols && gy >= 0 && gy < rows) {
          obstacles.add(pointKey(gx, gy));
        }
      }
    }
  };

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
    const cameFrom = new Map<string, string>();
    const gScore = new Map<string, number>([[startKey, 0]]);
    const fScore = new Map<string, number>([
      [
        startKey,
        Math.abs(startCell.gx - goalCell.gx) +
          Math.abs(startCell.gy - goalCell.gy),
      ],
    ]);

    const getLowestF = () => {
      let lowestKey = "";
      let lowestScore = Number.POSITIVE_INFINITY;
      openSet.forEach((key) => {
        const score = fScore.get(key) ?? Number.POSITIVE_INFINITY;
        if (score < lowestScore) {
          lowestScore = score;
          lowestKey = key;
        }
      });
      return lowestKey;
    };

    const neighbors = [
      { dx: 1, dy: 0 },
      { dx: -1, dy: 0 },
      { dx: 0, dy: 1 },
      { dx: 0, dy: -1 },
    ];

    const isBlocked = (gx: number, gy: number) => {
      const key = pointKey(gx, gy);
      if (key === allowStartKey || key === allowGoalKey) {
        return false;
      }
      return obstacles.has(key);
    };

    while (openSet.size > 0) {
      const currentKey = getLowestF();
      if (!currentKey) break;

      if (currentKey === goalKey) {
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
        if (
          neighborX < 0 ||
          neighborX >= cols ||
          neighborY < 0 ||
          neighborY >= rows
        ) {
          return;
        }
        if (isBlocked(neighborX, neighborY)) {
          return;
        }
        const neighborKey = pointKey(neighborX, neighborY);
        const tentativeG = (gScore.get(currentKey) ?? 0) + 1;
        if (
          tentativeG <
          (gScore.get(neighborKey) ?? Number.POSITIVE_INFINITY)
        ) {
          cameFrom.set(neighborKey, currentKey);
          gScore.set(neighborKey, tentativeG);
          const heuristic =
            Math.abs(neighborX - goalCell.gx) +
            Math.abs(neighborY - goalCell.gy);
          fScore.set(neighborKey, tentativeG + heuristic);
          openSet.add(neighborKey);
        }
      });
    }

    return [];
  };

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

  const routedPointsByEdge = new Map<string, Point[]>();
  const edgeKey = (source: string, target: string) => `${source}::${target}`;
  const edgeKeys = new Set(
    edges.map((edge) => edgeKey(edge.source, edge.target)),
  );
  const isBidirectional = (edge: Edge) =>
    edgeKeys.has(edgeKey(edge.target, edge.source));
  const isBidirectionalPrimary = (edge: Edge) =>
    isBidirectional(edge) && edge.source.localeCompare(edge.target) <= 0;

  // Use the smart routing anchors for all edges.

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

  const sortedEdges = [...edges].sort((a, b) => {
    const sourceA = nodeBoxMap.get(a.source);
    const targetA = nodeBoxMap.get(a.target);
    const sourceB = nodeBoxMap.get(b.source);
    const targetB = nodeBoxMap.get(b.target);
    if (!sourceA || !targetA || !sourceB || !targetB) return 0;
    const distA = Math.hypot(
      sourceA.center.x - targetA.center.x,
      sourceA.center.y - targetA.center.y,
    );
    const distB = Math.hypot(
      sourceB.center.x - targetB.center.x,
      sourceB.center.y - targetB.center.y,
    );
    return distB - distA;
  });

  sortedEdges.forEach((edge) => {
    const sourceNode = nodeBoxMap.get(edge.source);
    const targetNode = nodeBoxMap.get(edge.target);
    if (!sourceNode || !targetNode) {
      return;
    }

    const startPoint = getConnectionPoint(sourceNode, targetNode, "auto");
    const endPoint = getConnectionPoint(targetNode, sourceNode, "auto");
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

  const output: Edge[] = [];
  edges.forEach((edge) => {
    const bidirectional = isBidirectional(edge);
    if (bidirectional && !isBidirectionalPrimary(edge)) {
      return;
    }

    const routedPoints = routedPointsByEdge.get(edge.id);
    if (!routedPoints) {
      output.push(edge);
      return;
    }

    const stroke = bidirectional ? bidirectionalStroke : defaultStroke;
    const strokeWidth = bidirectional
      ? BIDIRECTIONAL_EDGE_WIDTH
      : DEFAULT_EDGE_WIDTH;
    const label = edge.data?.label;
    const pairIds = bidirectional
      ? bidirectionalPairs.get(pairKey(edge.source, edge.target))
      : undefined;

    const markerEnd =
      edge.markerEnd && typeof edge.markerEnd === "object"
        ? edge.markerEnd
        : undefined;
    const markerStart =
      edge.markerStart && typeof edge.markerStart === "object"
        ? edge.markerStart
        : undefined;

    output.push({
      ...edge,
      type: "routed",
      style: {
        ...(edge.style || {}),
        stroke,
        strokeWidth,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 16,
        height: 16,
        ...(markerEnd || {}),
        color: stroke,
      },
      markerStart: bidirectional
        ? {
            type: MarkerType.ArrowClosed,
            width: 16,
            height: 16,
            ...(markerStart || {}),
            color: stroke,
          }
        : markerStart,
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
