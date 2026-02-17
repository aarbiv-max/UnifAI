/**
 * useJointGraph – custom hook encapsulating the imperative JointJS graph
 * initialisation, data-fetching, layout, SVG injection, and sizing logic that
 * was previously inlined in the main useEffect of GraphDisplay.
 *
 * Uses the shared factory helpers from GraphDisplayHelpers so that node/link
 * creation is consistent between the display and creation canvases.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { flushSync } from "react-dom";

function safeFlushSync(fn: () => void): void {
  try {
    flushSync(fn);
  } catch (err) {
    console.warn("[useJointGraph] flushSync failed, falling back to batched update:", err);
    fn();
  }
}
import { dia } from "@joint/core";
import { DirectedGraph } from "@joint/layout-directed-graph";
import type { GraphFlow } from "@/components/agentic-ai/graphs/interfaces";
import {
  graphFlowToLayoutData,
  type LayoutNode,
} from "@/utils/graphFlowLayout";
import { getBlueprintInfo } from "@/api/blueprints";
import type { BuildingBlock } from "@/types/graph";
import {
  NODE_WIDTH,
  NODE_HEADER_HEIGHT,
  ELEMENT_BADGE_HEIGHT,
  ELEMENT_GAP,
  NODE_BODY_PADDING,
  LAYOUT_OPTS,
  FIT_PADDING,
  SCALE_CONTENT_TO_FIT_OPTS,
  injectSvgDefs,
  injectStatusGlowFilters,
  injectLinkAnimations,
  removeLinkAnimations,
  buildElementBlockMap,
  createJointPaper,
  setupPanZoom,
  createJointNode,
  createJointLink,
  type OverlayBadge,
  type OverlayHeader,
} from "@/components/agentic-ai/graphs/GraphDisplayHelpers";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface UseJointGraphOptions {
  blueprintId?: string;
  primaryHex?: string;
  /** Pre-fetched spec_dict – when provided, skips the network fetch entirely. */
  specDict?: any;
  showBackground?: boolean;
  interactive?: boolean;
  centerInView?: boolean;
  animated?: boolean;
}

export interface UseJointGraphReturn {
  containerRef: React.RefObject<HTMLDivElement>;
  graphRef: React.MutableRefObject<dia.Graph | null>;
  paperRef: React.MutableRefObject<dia.Paper | null>;
  layoutNodesRef: React.MutableRefObject<LayoutNode[]>;
  elementBlockRef: React.MutableRefObject<Map<string, BuildingBlock>>;
  loading: boolean;
  error: string | null;
  overlayBadges: OverlayBadge[];
  overlayHeaders: OverlayHeader[];
  paperTransform: { sx: number; sy: number; tx: number; ty: number };
  setPaperTransform: React.Dispatch<React.SetStateAction<{ sx: number; sy: number; tx: number; ty: number }>>;
  rebuildOverlays: () => void;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useJointGraph({
  blueprintId,
  primaryHex,
  specDict,
  showBackground = true,
  interactive = false,
  centerInView = false,
  animated = false,
}: UseJointGraphOptions): UseJointGraphReturn {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<dia.Graph | null>(null);
  const layoutNodesRef = useRef<LayoutNode[]>([]);
  const elementBlockRef = useRef<Map<string, BuildingBlock>>(new Map());
  const paperRef = useRef<dia.Paper | null>(null);
  const conditionalLinkIdsRef = useRef<Set<string>>(new Set());

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [overlayBadges, setOverlayBadges] = useState<OverlayBadge[]>([]);
  const [overlayHeaders, setOverlayHeaders] = useState<OverlayHeader[]>([]);
  const [paperTransform, setPaperTransform] = useState({
    sx: 1, sy: 1, tx: 0, ty: 0,
  });

  // Keep mutable ref so the async callback always reads the latest primary color.
  const primaryHexRef = useRef(primaryHex);
  primaryHexRef.current = primaryHex;

  // ── Rebuild overlay positions from current graph element positions ──
  const rebuildOverlays = useCallback(() => {
    const graph = graphRef.current;
    const nodes = layoutNodesRef.current;
    if (!graph || nodes.length === 0) return;

    const headers: OverlayHeader[] = [];
    const badges: OverlayBadge[] = [];

    for (const n of nodes) {
      const el = graph.getCell(n.id);
      if (!el) continue;
      const pos = (el as dia.Element).position();
      const size = (el as dia.Element).size();
      const hasElements = n.resolvedElements.length > 0;

      headers.push({
        nodeId: n.id,
        label: n.label,
        nodeType: n.type,
        hasElements,
        x: pos.x,
        y: pos.y,
        width: NODE_WIDTH,
        nodeHeight: size.height,
        nodeRid: n.nodeDefinition?.rid,
      });

      if (!hasElements) continue;
      const bodyStartY = pos.y + NODE_HEADER_HEIGHT + NODE_BODY_PADDING;
      const badgeInnerWidth = NODE_WIDTH - NODE_BODY_PADDING * 2;
      n.resolvedElements.forEach((re, i) => {
        badges.push({
          nodeId: n.id,
          element: re,
          x: pos.x + NODE_BODY_PADDING,
          y: bodyStartY + i * (ELEMENT_BADGE_HEIGHT + ELEMENT_GAP),
          width: badgeInnerWidth,
        });
      });
    }

    setOverlayHeaders(headers);
    setOverlayBadges(badges);
  }, []);

  // ── Main effect: fetch blueprint → build JointJS graph → layout ────
  useEffect(() => {
    if ((!blueprintId && !specDict) || !containerRef.current) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    setOverlayBadges([]);
    setOverlayHeaders([]);

    const { graph, paper } = createJointPaper(containerRef.current, {
      interactive: interactive ? { elementMove: true } : false,
      showBackground,
    });
    graphRef.current = graph;
    paperRef.current = paper;

    // Freeze the paper immediately so that adding nodes/edges does NOT
    // trigger SVG transform calculations.  This prevents the
    // "SVGMatrix is not invertible" error that occurs when the container
    // is inside an animating dialog (or any element with near-zero
    // dimensions at mount time).  We unfreeze once the layout is
    // complete and the container has valid dimensions.
    paper.freeze();

    // ── Pan + Zoom (shared helper, only for interactive mode) ──
    let cleanupPanZoom: (() => void) | null = null;
    if (interactive) {
      cleanupPanZoom = setupPanZoom(paper, (t) => {
        safeFlushSync(() => setPaperTransform(t));
      });
    }

    let cancelled = false;

    /**
     * Wait until a container element has non-trivial dimensions.
     * Useful when the component is mounted inside an animating dialog
     * whose container starts at near-zero size.  Returns `true` when
     * valid dimensions are detected, `false` if cancelled or timed-out.
     */
    const waitForValidSize = (
      el: HTMLElement,
      minDim = 50,
      timeoutMs = 3000,
    ): Promise<boolean> =>
      new Promise((resolve) => {
        if (el.clientWidth >= minDim && el.clientHeight >= minDim) {
          resolve(true);
          return;
        }
        const ro = new ResizeObserver(() => {
          if (cancelled) { ro.disconnect(); resolve(false); return; }
          if (el.clientWidth >= minDim && el.clientHeight >= minDim) {
            ro.disconnect();
            clearTimeout(timer);
            resolve(true);
          }
        });
        ro.observe(el);
        const timer = setTimeout(() => {
          ro.disconnect();
          // Last-ditch check — container may be big enough now
          resolve(el.clientWidth >= minDim && el.clientHeight >= minDim);
        }, timeoutMs);
      });

    (async () => {
      try {
        // Use provided specDict directly if available, otherwise fetch single blueprint
        let spec: GraphFlow;
        if (specDict) {
          spec = specDict as GraphFlow;
        } else if (blueprintId) {
          const blueprintInfo = await getBlueprintInfo(blueprintId);
          if (cancelled) return;
          if (!blueprintInfo?.spec_dict) {
            setError("Workflow not found");
            setLoading(false);
            return;
          }
          spec = blueprintInfo.spec_dict as GraphFlow;
        } else {
          setLoading(false);
          return;
        }
        const { nodes: layoutNodes, edges: layoutEdges } =
          graphFlowToLayoutData(spec);
        layoutNodesRef.current = layoutNodes;
        elementBlockRef.current = buildElementBlockMap(layoutNodes, spec);

        if (layoutNodes.length === 0) {
          setError("No steps in workflow");
          setLoading(false);
          return;
        }

        // SVG defs: gradients + shadow + status glow filters
        const primaryNow = primaryHexRef.current || "#8b5cf6";
        injectSvgDefs(paper.el, primaryNow);
        injectStatusGlowFilters(paper.el);

        // Create JointJS nodes (using shared factory)
        for (const n of layoutNodes) {
          createJointNode(graph, n.id, n.type, { x: 0, y: 0 }, n.resolvedElements.length);
        }

        // Create edges (using shared factory)
        const linkColor = primaryHexRef.current?.startsWith("#")
          ? primaryHexRef.current
          : `#${primaryHexRef.current || "8b5cf6"}`;
        const edgeColors = {
          primary: linkColor,
          bidi: linkColor,
          conditional: "#94a3b8",
        };

        conditionalLinkIdsRef.current.clear();
        for (const e of layoutEdges) {
          const linkId = `${e.source}-${e.target}`;
          const link = createJointLink(graph, linkId, e.source, e.target, edgeColors, {
            isConditional: e.isConditional,
          });
          if (e.isConditional) conditionalLinkIdsRef.current.add(link.id as string);
        }

        // Auto-layout
        DirectedGraph.layout(graph, LAYOUT_OPTS);

        // Force final_answer_node to the bottom
        const typeById = new Map(layoutNodes.map((n) => [n.id, n.type]));
        let maxBottom = 0;
        graph.getElements().forEach((el) => {
          if (typeById.get(el.id as string) !== "final_answer_node") {
            const b = el.getBBox();
            maxBottom = Math.max(maxBottom, b.y + b.height);
          }
        });
        graph.getElements().forEach((el) => {
          if (typeById.get(el.id as string) === "final_answer_node") {
            const pos = el.position();
            el.position(pos.x, maxBottom + LAYOUT_OPTS.rankSep);
          }
        });

        // Recompute bounding box after manual repositioning of final_answer_node
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        graph.getElements().forEach((el) => {
          const b = el.getBBox();
          minX = Math.min(minX, b.x);
          minY = Math.min(minY, b.y);
          maxX = Math.max(maxX, b.x + b.width);
          maxY = Math.max(maxY, b.y + b.height);
        });
        const actualBbox = {
          width: maxX - (Number.isFinite(minX) ? minX : 0),
          height: maxY - (Number.isFinite(minY) ? minY : 0),
        };

        // ── Ensure container has real dimensions before unfreezing ──
        // When the graph lives inside an animating dialog the container
        // may still be near-zero size at this point.  We MUST wait for
        // valid dimensions before unfreezing the paper, otherwise
        // JointJS link-view routing will hit "SVGMatrix is not invertible".
        const container = containerRef.current;
        if (!container) return;

        let cw = container.clientWidth ?? 0;
        let ch = container.clientHeight ?? 0;

        if (cw < 50 || ch < 50) {
          const ok = await waitForValidSize(container);
          if (cancelled || !ok) return;
          cw = container.clientWidth;
          ch = container.clientHeight;
        }

        try {
          if (centerInView && cw > 0 && ch > 0) {
            paper.setDimensions(cw, ch);
            paper.transformToFitContent(SCALE_CONTENT_TO_FIT_OPTS);
          } else {
            paper.setDimensions(
              Math.max(actualBbox.width + FIT_PADDING * 2, cw > 0 ? cw : 400),
              Math.max(actualBbox.height + FIT_PADDING * 2, ch > 0 ? ch : 300),
            );
          }
        } catch {
          // Container may not be visible yet (e.g. carousel panel is collapsed).
          // The ResizeObserver will handle fitting once it gains a valid size.
        }

        // All geometry is settled — unfreeze the paper so JointJS renders
        // the SVG elements with valid transforms.
        paper.unfreeze();

        if (animated) {
          injectLinkAnimations(paper.el);
        }

        const scale = paper.scale();
        const translate = paper.translate();
        setPaperTransform({ sx: scale.sx, sy: scale.sy, tx: translate.tx, ty: translate.ty });

        rebuildOverlays();
        if (interactive) graph.on("change:position", () => { safeFlushSync(() => rebuildOverlays()); });

        setLoading(false);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load workflow");
        setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
      if (cleanupPanZoom) cleanupPanZoom();
      graph.off("change:position");
      removeLinkAnimations(paper.el);
      paper.remove();
      graph.clear();
      graphRef.current = null;
      paperRef.current = null;
      layoutNodesRef.current = [];
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [blueprintId, specDict, showBackground, interactive, centerInView, animated, rebuildOverlays]);

  // ── Lightweight theme-color update (avoids full graph rebuild) ──────
  useEffect(() => {
    const paper = paperRef.current;
    const graph = graphRef.current;
    if (!paper || !graph) return;

    const primaryNow = primaryHex || "#8b5cf6";
    injectSvgDefs(paper.el, primaryNow);

    const linkColor = primaryNow.startsWith("#") ? primaryNow : `#${primaryNow}`;
    for (const link of graph.getLinks()) {
      if (conditionalLinkIdsRef.current.has(link.id as string)) continue;
      link.attr("line/stroke", linkColor);
      link.attr("line/sourceMarker/fill", linkColor);
      link.attr("line/targetMarker/fill", linkColor);
    }
  }, [primaryHex]);

  // ── Auto-fit paper when container resizes (e.g. console open/close, carousel mode switch) ─
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !centerInView) return;

    // Minimum container size required to attempt fitting.  Prevents
    // non-invertible SVGMatrix errors when the container is mid-CSS-transition
    // or collapsed to near-zero during carousel mode switches.
    const MIN_DIMENSION = 50;
    let resizeTimerId: ReturnType<typeof setTimeout> | null = null;

    const observer = new ResizeObserver(() => {
      // Debounce resize events briefly.  The MIN_DIMENSION guard below already
      // filters out the dangerous tiny-container frames during CSS transitions,
      // so we only need a short debounce to batch rapid-fire ResizeObserver
      // callbacks without adding perceptible delay.
      if (resizeTimerId) clearTimeout(resizeTimerId);
      resizeTimerId = setTimeout(() => {
        const paper = paperRef.current;
        const graph = graphRef.current;
        if (!paper || !graph || graph.getElements().length === 0) return;

        const cw = container.clientWidth;
        const ch = container.clientHeight;
        if (cw < MIN_DIMENSION || ch < MIN_DIMENSION) return;

        try {
          // Reset to identity transform first.  If the paper was previously
          // scaled to near-zero (e.g. the panel was collapsed), the internal
          // SVGMatrix is singular and any setDimensions / transformToFitContent
          // call would throw "The matrix is not invertible".
          paper.scale(1, 1);
          paper.translate(0, 0);
          paper.setDimensions(cw, ch);
          paper.transformToFitContent(SCALE_CONTENT_TO_FIT_OPTS);
        } catch {
          // Transition-related SVGMatrix error — safe to ignore; the next
          // resize event (after the transition finishes) will succeed.
          return;
        }

        const scale = paper.scale();
        const translate = paper.translate();
        setPaperTransform({ sx: scale.sx, sy: scale.sy, tx: translate.tx, ty: translate.ty });
        rebuildOverlays();
      }, 10);
    });

    observer.observe(container);
    return () => {
      observer.disconnect();
      if (resizeTimerId) clearTimeout(resizeTimerId);
    };
  }, [centerInView, rebuildOverlays]);

  return {
    containerRef,
    graphRef,
    paperRef,
    layoutNodesRef,
    elementBlockRef,
    loading,
    error,
    overlayBadges,
    overlayHeaders,
    paperTransform,
    setPaperTransform,
    rebuildOverlays,
  };
}
