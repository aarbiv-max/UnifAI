import { useMemo } from "react";
import { Edge, Node } from "reactflow";
import { buildSmartEdges } from "@/components/agentic-ai/graphs/graphRouting";
import { useTheme } from "@/contexts/ThemeContext";

const DEFAULT_PRIMARY_COLOR = "#7C3AED";

/**
 * Hook that transforms ReactFlow edges into smart-routed edges.
 * Memoizes the result to avoid recalculating on every render.
 * 
 * @param nodes - ReactFlow nodes for routing calculations
 * @param edges - Original edges to transform
 * @param primaryColor - Optional primary color override. If not provided, uses theme's primaryHex.
 * @returns Edges with orthogonal routing and bidirectional handling
 */
export function useSmartEdges(
  nodes: Node[],
  edges: Edge[],
  primaryColor?: string,
): Edge[] {
  const { primaryHex } = useTheme();
  const resolvedColor = primaryColor ?? primaryHex ?? DEFAULT_PRIMARY_COLOR;

  return useMemo(
    () => buildSmartEdges(nodes, edges, resolvedColor),
    [nodes, edges, resolvedColor],
  );
}
