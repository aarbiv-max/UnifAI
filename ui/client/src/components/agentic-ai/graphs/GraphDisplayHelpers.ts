/**
 * Pure helpers and constants shared by both the read-only GraphDisplay and the
 * interactive GraphCanvas (creation).
 *
 * Nothing in this file depends on React state or hooks.
 */

import { dia, shapes } from "@joint/core";
import type { GraphFlow } from "./interfaces";
import type { LayoutNode, ResolvedElement } from "@/utils/graphFlowLayout";
import { extractUidFromRef } from "@/utils/graphFlowLayout";
import { getCategoryDisplay } from "@/components/shared/helpers";
import type { BuildingBlock } from "@/types/graph";

// ---------------------------------------------------------------------------
// Layout constants
// ---------------------------------------------------------------------------

export const NODE_WIDTH = 320;
export const NODE_HEADER_HEIGHT = 52;
export const ELEMENT_BADGE_HEIGHT = 26;
export const ELEMENT_GAP = 4;
export const NODE_BODY_PADDING = 8;

export const LAYOUT_OPTS = {
  rankDir: "TB" as const,
  nodeSep: 60,
  edgeSep: 40,
  rankSep: 80,
  marginX: 32,
  marginY: 32,
  setVertices: true,
  disableOptimalOrderHeuristic: false,
};

/** Shared padding used when fitting the graph into the viewport. */
export const FIT_PADDING = 40;

/** Shared options passed to `paper.transformToFitContent()`. */
export const SCALE_CONTENT_TO_FIT_OPTS = {
  padding: FIT_PADDING,
  preserveAspectRatio: true,
  verticalAlign: "middle" as const,
  horizontalAlign: "middle" as const,
  useModelGeometry: true,
};

// ---------------------------------------------------------------------------
// Badge styling constants (frosted-glass look on dark nodes)
// ---------------------------------------------------------------------------

export const BADGE_BG = "rgba(0,0,0,0.28)";
export const BADGE_BORDER = "rgba(255,255,255,0.10)";
export const BADGE_HOVER_BG = "rgba(255,255,255,0.10)";

// ---------------------------------------------------------------------------
// Overlay data interfaces
// ---------------------------------------------------------------------------

/** Positioned element badge data for overlay rendering. */
export interface OverlayBadge {
  nodeId: string;
  element: ResolvedElement;
  x: number;
  y: number;
  width: number;
}

/** Header overlay data (title text + icon + separator). */
export interface OverlayHeader {
  nodeId: string;
  label: string;
  nodeType: string;
  hasElements: boolean;
  x: number;
  y: number;
  width: number;
  /** Full node height so we know the rendered size. */
  nodeHeight: number;
  /** Node RID from its definition – used for validation result lookups. */
  nodeRid: string | undefined;
}

// ---------------------------------------------------------------------------
// Category type → plural key mapping (used by overlay badges & block map)
// ---------------------------------------------------------------------------

export const CATEGORY_TYPE_TO_PLURAL: Record<string, string> = {
  llm: "llms",
  tool: "tools",
  retriever: "retrievers",
  provider: "providers",
};

// ---------------------------------------------------------------------------
// Node helpers
// ---------------------------------------------------------------------------

/** Returns an emoji icon matching the node type. */
export function nodeIconForType(nodeType: string): string {
  if (nodeType === "user_question_node") return "\uD83D\uDCAC"; // 💬
  if (nodeType === "final_answer_node") return "\uD83E\uDD16"; // 🤖
  // Deterministic pick from a set based on type-name hash
  const icons = [
    "\uD83D\uDD0D", // 🔍
    "\uD83D\uDCDA", // 📚
    "\uD83E\uDDE0", // 🧠
    "\uD83D\uDD0E", // 🔎
    "\uD83D\uDD27", // 🔧
    "\u270D\uFE0F", // ✍️
  ];
  const hash = nodeType
    .split("")
    .reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
  return icons[hash % icons.length];
}

/** Compute the total pixel height of a node given its element count. */
export function computeNodeHeight(elementCount: number): number {
  if (elementCount === 0) return NODE_HEADER_HEIGHT;
  const bodyHeight =
    NODE_BODY_PADDING * 2 +
    elementCount * ELEMENT_BADGE_HEIGHT +
    Math.max(0, elementCount - 1) * ELEMENT_GAP;
  return NODE_HEADER_HEIGHT + bodyHeight;
}

/** Height of a single condition badge row inside a node. */
export const CONDITION_BADGE_HEIGHT = 28;
export const CONDITION_GAP = 4;

/**
 * Full node height accounting for both sub-element badges and condition
 * badges. Used by the creation canvas where conditions are attached to nodes.
 */
export function computeCreationNodeHeight(
  elementCount: number,
  conditionCount: number,
): number {
  let h = computeNodeHeight(elementCount);
  if (conditionCount > 0) {
    h +=
      NODE_BODY_PADDING +
      conditionCount * CONDITION_BADGE_HEIGHT +
      Math.max(0, conditionCount - 1) * CONDITION_GAP +
      NODE_BODY_PADDING;
  }
  return h;
}

/** Returns the SVG gradient fill reference for a node type. */
export function nodeFillForType(type: string): string {
  if (type === "user_question_node" || type === "final_answer_node") {
    return "url(#agentGradientSpecial)";
  }
  return "url(#agentGradient)";
}

// ---------------------------------------------------------------------------
// SVG defs injection (gradients + shadow filter)
// ---------------------------------------------------------------------------

/**
 * Inject SVG `<defs>` (gradients + drop-shadow filter) into the JointJS
 * paper SVG element.  Idempotent – safe to call on the same element twice.
 *
 * **Why direct SVG DOM manipulation is necessary here:**
 *
 * SVG `fill` with gradients (`url(#agentGradient)`) requires a
 * `<linearGradient>` definition inside the same SVG's `<defs>`.  There is
 * no CSS-only alternative for SVG gradient fills.  JointJS does not expose
 * a public API for injecting custom `<defs>`, so we add them directly.
 *
 * This is safe because:
 * 1. We only *append* to `<defs>` – never remove or modify existing JointJS
 *    elements.
 * 2. All injected elements use stable IDs that JointJS does not use
 *    (`agentGradient`, `agentGradientSpecial`, `nodeShadow`).
 * 3. The function is idempotent (upsert pattern) so repeated calls are
 *    harmless (e.g. on theme change).
 */
export function injectSvgDefs(
  paperEl: HTMLElement,
  primaryHex: string,
  darkSlate = "#1a1f2e",
): void {
  const svg =
    paperEl.tagName === "svg" ? paperEl : paperEl.querySelector("svg");
  if (!svg) return;

  let defs = svg.querySelector("defs");
  if (!defs) {
    defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    svg.insertBefore(defs, svg.firstChild);
  }

  // Helper to upsert a linear gradient (uses DOM APIs instead of innerHTML)
  const upsertGradient = (id: string, stopColors: [string, string]) => {
    const existing = defs!.querySelector(`#${id}`);
    if (existing) existing.remove();
    const g = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "linearGradient",
    );
    g.setAttribute("id", id);
    g.setAttribute("x1", "0%");
    g.setAttribute("y1", "0%");
    g.setAttribute("x2", "100%");
    g.setAttribute("y2", "100%");

    const offsets = ["0%", "100%"];
    stopColors.forEach((color, i) => {
      const stop = document.createElementNS("http://www.w3.org/2000/svg", "stop");
      stop.setAttribute("offset", offsets[i]);
      stop.setAttribute("stop-color", color);
      g.appendChild(stop);
    });

    defs!.appendChild(g);
  };

  // Main gradient: dark slate → primary
  upsertGradient("agentGradient", [darkSlate, primaryHex]);
  // Special gradient: dark slate → dark teal (user_question / final_answer)
  upsertGradient("agentGradientSpecial", [darkSlate, "#003f5c"]);

  // Drop-shadow filter (only added once)
  if (!defs.querySelector("#nodeShadow")) {
    const filter = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "filter",
    );
    filter.setAttribute("id", "nodeShadow");
    filter.setAttribute("x", "-20%");
    filter.setAttribute("y", "-20%");
    filter.setAttribute("width", "140%");
    filter.setAttribute("height", "140%");
    const feDrop = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "feDropShadow",
    );
    feDrop.setAttribute("dx", "0");
    feDrop.setAttribute("dy", "4");
    feDrop.setAttribute("stdDeviation", "8");
    feDrop.setAttribute("flood-color", "#000");
    feDrop.setAttribute("flood-opacity", "0.35");
    filter.appendChild(feDrop);
    defs.appendChild(filter);
  }
}

// ---------------------------------------------------------------------------
// Live-status visual constants
// ---------------------------------------------------------------------------

export const STATUS_STYLES = {
  PROGRESS: {
    stroke: "rgba(59, 130, 246, 0.85)",
    strokeWidth: 2.5,
    filter: "url(#progressGlow)",
    dotColor: "rgb(59, 130, 246)",
    bgColor: "rgba(59, 130, 246, 0.2)",
    label: "Processing",
    /** CSS box-shadow for the HTML overlay border glow. */
    boxShadow: "0 0 12px rgba(59,130,246,0.5), 0 0 4px rgba(59,130,246,0.3)",
  },
  DONE: {
    stroke: "rgba(34, 197, 94, 0.7)",
    strokeWidth: 2,
    filter: "url(#doneGlow)",
    dotColor: "rgb(34, 197, 94)",
    bgColor: "rgba(34, 197, 94, 0.2)",
    label: "Complete",
    boxShadow: "0 0 8px rgba(34,197,94,0.4), 0 0 3px rgba(34,197,94,0.25)",
  },
  IDLE: {
    stroke: "rgba(255,255,255,0.12)",
    strokeWidth: 1,
    filter: "url(#nodeShadow)",
    dotColor: "",
    bgColor: "",
    label: "",
    boxShadow: "none",
  },
} as const;

// ---------------------------------------------------------------------------
// Live-status SVG glow filter injection
// ---------------------------------------------------------------------------

/**
 * Inject `progressGlow` and `doneGlow` SVG filter defs into the paper.
 * Idempotent – safe to call multiple times.
 *
 * **Why SVG filters instead of CSS `filter`:**
 *
 * JointJS sets the SVG `filter` *attribute* on `<rect>` elements (via
 * `el.attr("body/filter", …)`).  The SVG `filter` attribute only accepts
 * `url(#…)` references to SVG `<filter>` elements – it cannot take CSS
 * filter functions like `drop-shadow(…)`.  (CSS `filter` is a *property*
 * that can be set via `style`, but JointJS attrs target SVG attributes.)
 *
 * As with gradients, we only append to `<defs>` and use stable IDs that
 * don't collide with JointJS internals, so this is safe for upgrades.
 */
export function injectStatusGlowFilters(paperEl: HTMLElement): void {
  const svg =
    paperEl.tagName === "svg" ? paperEl : paperEl.querySelector("svg");
  if (!svg) return;

  const defs = svg.querySelector("defs");
  if (!defs) return;

  // Helper to create an SVG feDropShadow element via DOM APIs
  const mkDropShadow = (attrs: Record<string, string>) => {
    const fe = document.createElementNS("http://www.w3.org/2000/svg", "feDropShadow");
    for (const [k, v] of Object.entries(attrs)) fe.setAttribute(k, v);
    return fe;
  };

  const upsertFilter = (
    id: string,
    bounds: { x: string; y: string; w: string; h: string },
    shadows: Record<string, string>[],
  ) => {
    if (defs.querySelector(`#${id}`)) return;
    const f = document.createElementNS("http://www.w3.org/2000/svg", "filter");
    f.setAttribute("id", id);
    f.setAttribute("x", bounds.x);
    f.setAttribute("y", bounds.y);
    f.setAttribute("width", bounds.w);
    f.setAttribute("height", bounds.h);
    shadows.forEach((s) => f.appendChild(mkDropShadow(s)));
    defs.appendChild(f);
  };

  upsertFilter(
    "progressGlow",
    { x: "-30%", y: "-30%", w: "160%", h: "160%" },
    [
      { dx: "0", dy: "0", stdDeviation: "6", "flood-color": "rgba(59,130,246,0.5)", "flood-opacity": "0.8" },
      { dx: "0", dy: "2", stdDeviation: "4", "flood-color": "#000", "flood-opacity": "0.25" },
    ],
  );

  upsertFilter(
    "doneGlow",
    { x: "-20%", y: "-20%", w: "140%", h: "140%" },
    [
      { dx: "0", dy: "0", stdDeviation: "4", "flood-color": "rgba(34,197,94,0.4)", "flood-opacity": "0.6" },
      { dx: "0", dy: "2", stdDeviation: "4", "flood-color": "#000", "flood-opacity": "0.25" },
    ],
  );
}

// ---------------------------------------------------------------------------
// Link animation injection
// ---------------------------------------------------------------------------

/**
 * Add a flowing stroke-dasharray animation to every link path in the SVG.
 * Idempotent – existing `<animate>` children are removed before appending new
 * ones so that calling this function multiple times on the same SVG does not
 * stack duplicate animations.
 */
export function injectLinkAnimations(paperEl: HTMLElement): void {
  const svgEl = paperEl.querySelector("svg");
  if (!svgEl) return;

  const linkPaths = svgEl.querySelectorAll("[joint-selector='line']");
  linkPaths.forEach((path) => {
    // Remove any existing <animate> elements to prevent duplication
    path.querySelectorAll("animate").forEach((a) => a.remove());

    path.setAttribute("stroke-dasharray", "8 4");
    const animate = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "animate",
    );
    animate.setAttribute("attributeName", "stroke-dashoffset");
    animate.setAttribute("from", "0");
    animate.setAttribute("to", "-12"); // 8+4 = 12 → one pattern cycle
    animate.setAttribute("dur", "0.8s");
    animate.setAttribute("repeatCount", "indefinite");
    path.appendChild(animate);
  });
}

/** Remove link animations previously injected by injectLinkAnimations. */
export function removeLinkAnimations(paperEl: HTMLElement): void {
  const svgEl = paperEl.querySelector("svg");
  if (!svgEl) return;

  const linkPaths = svgEl.querySelectorAll("[joint-selector='line']");
  linkPaths.forEach((path) => {
    path.removeAttribute("stroke-dasharray");
    // Remove all <animate> children
    const animates = path.querySelectorAll("animate");
    animates.forEach((a) => a.remove());
  });
}

// ---------------------------------------------------------------------------
// Element block map builder
// ---------------------------------------------------------------------------

/**
 * Build a `Map<elementId, BuildingBlock>` from the layout nodes and the
 * original GraphFlow spec. Used by overlay badges to show resource details.
 */
export function buildElementBlockMap(
  layoutNodes: LayoutNode[],
  spec: GraphFlow,
): Map<string, BuildingBlock> {
  const map = new Map<string, BuildingBlock>();

  layoutNodes.forEach((n) => {
    n.resolvedElements.forEach((el) => {
      const category = CATEGORY_TYPE_TO_PLURAL[el.type] || "retrievers";
      const catList = (spec as unknown as Record<string, unknown[]>)[category];
      const def = catList?.find((d: unknown) => {
        const entry = d as { rid?: string };
        return (
          extractUidFromRef(entry.rid || "") === el.id || entry.rid === el.id
        );
      });
      if (!def) return;

      const d = def as {
        rid: string;
        name: string;
        type: string;
        config?: unknown;
        nested_refs?: string[];
      };
      const display = getCategoryDisplay(category);
      map.set(el.id, {
        id: d.rid,
        type: d.type,
        label: d.name,
        color: display.color,
        description: `${category}/${d.type} - ${d.name}`,
        workspaceData: {
          rid: d.rid,
          name: d.name,
          category,
          type: d.type,
          config: d.config ?? {},
          version: 1,
          created: "",
          updated: "",
          nested_refs: d.nested_refs ?? [],
        },
      });
    });
  });

  return map;
}

// ---------------------------------------------------------------------------
// Shared JointJS factories – used by both display and creation canvases
// ---------------------------------------------------------------------------

/** Standard paper grid options. */
export const PAPER_GRID_OPTS = {
  name: "doubleMesh" as const,
  args: [
    { color: "rgba(255,255,255,0.06)", thickness: 1 },
    { color: "rgba(255,255,255,0.12)", scaleFactor: 4, thickness: 1 },
  ],
};

/** Create a `dia.Graph` + `dia.Paper` with consistent styling. */
export function createJointPaper(
  container: HTMLElement,
  opts: {
    interactive?: boolean | { elementMove: boolean };
    showBackground?: boolean;
  } = {},
): { graph: dia.Graph; paper: dia.Paper } {
  const namespace = { ...shapes };
  const graph = new dia.Graph({}, { cellNamespace: namespace });
  const interactive = opts.interactive ?? false;
  const showBackground = opts.showBackground ?? true;

  const paper = new dia.Paper({
    model: graph,
    cellViewNamespace: namespace,
    width: "100%",
    height: "100%",
    interactive,
    background: showBackground ? { color: "transparent" } : undefined,
    gridSize: 16,
    drawGrid: showBackground ? PAPER_GRID_OPTS : false,
  });

  container.replaceChildren(paper.el);
  paper.el.classList.add("joint-paper");
  return { graph, paper };
}

/**
 * Wire pan (drag on blank) and mouse-wheel zoom onto a `dia.Paper`.
 * Returns a cleanup function that removes the global listeners.
 */
export function setupPanZoom(
  paper: dia.Paper,
  onTransformChange: (t: { sx: number; sy: number; tx: number; ty: number }) => void,
): () => void {
  let isPanning = false;
  let panStartX = 0;
  let panStartY = 0;

  paper.el.style.cursor = "grab";

  paper.on("blank:pointerdown", (evt: dia.Event) => {
    isPanning = true;
    const ne = (evt as any).originalEvent ?? evt;
    panStartX = ne.clientX;
    panStartY = ne.clientY;
    paper.el.style.cursor = "grabbing";
  });

  const onPointerMove = (evt: PointerEvent) => {
    if (!isPanning) return;
    const dx = evt.clientX - panStartX;
    const dy = evt.clientY - panStartY;
    panStartX = evt.clientX;
    panStartY = evt.clientY;
    const t = paper.translate();
    paper.translate(t.tx + dx, t.ty + dy);
    emitTransform();
  };

  const onPointerUp = () => {
    if (!isPanning) return;
    isPanning = false;
    paper.el.style.cursor = "grab";
  };

  document.addEventListener("pointermove", onPointerMove);
  document.addEventListener("pointerup", onPointerUp);

  const ZOOM_FACTOR = 1.04;
  const MIN_ZOOM = 0.1;
  const MAX_ZOOM = 4;

  const onWheel = (_evt: dia.Event, ox: number, oy: number, delta: number) => {
    const old = paper.scale().sx;
    const ns = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, delta > 0 ? old * ZOOM_FACTOR : old / ZOOM_FACTOR));
    if (ns === old) return;
    const t = paper.translate();
    const sd = ns / old;
    paper.scale(ns, ns);
    paper.translate(t.tx - ox * (sd - 1) * old, t.ty - oy * (sd - 1) * old);
    emitTransform();
  };

  paper.on("blank:mousewheel", onWheel);
  paper.on(
    "cell:mousewheel",
    (_cv: unknown, evt: dia.Event, ox: number, oy: number, delta: number) => onWheel(evt, ox, oy, delta),
  );

  function emitTransform() {
    const s = paper.scale();
    const tr = paper.translate();
    onTransformChange({ sx: s.sx, sy: s.sy, tx: tr.tx, ty: tr.ty });
  }

  return () => {
    document.removeEventListener("pointermove", onPointerMove);
    document.removeEventListener("pointerup", onPointerUp);
  };
}

/** Create a JointJS rectangle node with shared visual styling. */
export function createJointNode(
  graph: dia.Graph,
  id: string,
  type: string,
  position: { x: number; y: number },
  elementCount: number,
): dia.Element {
  return new shapes.standard.Rectangle({
    id,
    position,
    size: { width: NODE_WIDTH, height: computeNodeHeight(elementCount) },
    attrs: {
      body: {
        fill: nodeFillForType(type),
        stroke: STATUS_STYLES.IDLE.stroke,
        strokeWidth: STATUS_STYLES.IDLE.strokeWidth,
        rx: 12,
        ry: 12,
        filter: STATUS_STYLES.IDLE.filter,
      },
      label: { text: "" },
    },
  }).addTo(graph);
}

export interface LinkStyleOptions {
  isConditional?: boolean;
  isBidirectional?: boolean;
  branchLabel?: string;
}

/** Create a JointJS link with shared visual styling.
 *  `primaryColor` = primary theme color for regular edges.
 *  `bidiColor`    = color for bidirectional edges (defaults to primaryLight green).
 *  `condColor`    = color for conditional edges.
 */
export function createJointLink(
  graph: dia.Graph,
  id: string,
  sourceId: string,
  targetId: string,
  colors: { primary: string; bidi: string; conditional: string },
  opts: LinkStyleOptions = {},
): dia.Link {
  const { isConditional, isBidirectional, branchLabel } = opts;

  let strokeColor: string;
  let strokeWidth: number;
  let dashArray: string | undefined;
  let markerColor: string;

  if (isConditional) {
    strokeColor = `${colors.conditional}cc`;
    strokeWidth = 1.5;
    dashArray = "6 3";
    markerColor = colors.conditional;
  } else if (isBidirectional) {
    strokeColor = colors.bidi;
    strokeWidth = 2.5;
    dashArray = undefined;
    markerColor = colors.bidi;
  } else {
    strokeColor = colors.primary;
    strokeWidth = 2;
    dashArray = undefined;
    markerColor = colors.primary;
  }

  const link = new shapes.standard.Link({
    id,
    source: { id: sourceId },
    target: { id: targetId },
    attrs: {
      line: {
        stroke: strokeColor,
        strokeWidth,
        strokeDasharray: dashArray,
        sourceMarker: { type: "circle" as const, r: isConditional ? 3 : 4, fill: markerColor },
        targetMarker: { type: "classic" as const, size: isConditional ? 10 : 12, fill: markerColor },
      },
    },
    labels: branchLabel
      ? [
          {
            position: 0.5,
            attrs: {
              text: { text: branchLabel, fill: "#d1d5db", fontSize: 10 },
              rect: { fill: "#1f2937", stroke: "#374151", rx: 3, ry: 3 },
            },
          },
        ]
      : [],
  }).addTo(graph);
  return link;
}

/**
 * Extract `$ref:` IDs from a config object and resolve them against a block
 * list. Returns an array of `{ id, name, type, category }` for badge rendering.
 */
export interface ResolvedRef {
  id: string;
  name: string;
  type: string;
  category: string;
}

export function resolveConfigRefs(
  config: Record<string, unknown> | undefined,
  allBlocks: BuildingBlock[],
): ResolvedRef[] {
  if (!config) return [];
  const refIds: string[] = [];
  const seen = new Set<string>();
  const traverse = (obj: unknown) => {
    if (typeof obj === "string" && obj.startsWith("$ref:")) {
      const id = obj.substring(5);
      if (!seen.has(id)) { seen.add(id); refIds.push(id); }
    } else if (Array.isArray(obj)) {
      obj.forEach(traverse);
    } else if (obj && typeof obj === "object") {
      Object.values(obj).forEach(traverse);
    }
  };
  traverse(config);

  return refIds.map((id) => {
    const block = allBlocks.find(
      (b) => b.workspaceData?.rid === id || b.id === id,
    );
    return {
      id,
      name: block?.label || id,
      type: block?.type || "unknown",
      category: block?.workspaceData?.category || "default",
    };
  });
}
