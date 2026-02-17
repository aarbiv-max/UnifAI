import React, { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { flushSync } from "react-dom";
import { dia } from "@joint/core";
import { Card, CardContent } from "@/components/ui/card";
import { Plus, X, GitBranch, Trash2, ZoomIn, ZoomOut, Maximize, Lock, Unlock } from "lucide-react";
import { Button } from "@/components/ui/button";
import GraphHeader from "./GraphHeader";
import * as yaml from "js-yaml";
import { useTheme } from "@/contexts/ThemeContext";
import { deriveThemeColors } from "@/lib/colorUtils";
import { getCategoryDisplay } from "@/components/shared/helpers";
import type { CanvasNode, CanvasEdge, BuildingBlock } from "@/types/graph";
import {
  NODE_WIDTH,
  NODE_HEADER_HEIGHT,
  NODE_BODY_PADDING,
  ELEMENT_BADGE_HEIGHT,
  ELEMENT_GAP,
  BADGE_BG,
  BADGE_BORDER,
  STATUS_STYLES,
  CATEGORY_TYPE_TO_PLURAL,
  SCALE_CONTENT_TO_FIT_OPTS,
  nodeIconForType,
  computeCreationNodeHeight,
  createJointPaper,
  setupPanZoom,
  createJointNode,
  createJointLink,
  injectSvgDefs,
  injectStatusGlowFilters,
  resolveConfigRefs,
  type ResolvedRef,
} from "./GraphDisplayHelpers";

function safeFlushSync(fn: () => void): void {
  try {
    flushSync(fn);
  } catch {
    fn();
  }
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface GraphCanvasProps {
  canvasNodes: CanvasNode[];
  canvasEdges: CanvasEdge[];
  allBlocks: BuildingBlock[];
  yamlFlow?: any;
  connectionSource: string | null;
  onNodeClick: (nodeId: string) => void;
  onCancelConnection: () => void;
  onAddNode: (block: BuildingBlock, position: { x: number; y: number }) => string;
  onDeleteNode: (nodeId: string) => void;
  onDeleteEdge: (sourceId: string, targetId: string) => void;
  onAttachCondition: (nodeId: string, condition: BuildingBlock) => void;
  onRemoveCondition: (nodeId: string, conditionRid: string) => void;
  onClearGraph: () => void;
  onSaveGraph: () => void;
  onBack?: () => void;
  isGraphValid?: boolean;
  isDraggingCondition?: boolean;
  onValidate?: () => void;
  isValidating?: boolean;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SELECTED_STROKE = "#60a5fa";
const SELECTED_STROKE_WIDTH = 3;
const CLICK_THRESHOLD = 5;
const ZOOM_STEP = 1.25;
const MIN_ZOOM = 0.1;
const MAX_ZOOM = 4;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const GraphCanvas: React.FC<GraphCanvasProps> = ({
  canvasNodes,
  canvasEdges,
  allBlocks,
  yamlFlow,
  connectionSource,
  onNodeClick,
  onCancelConnection,
  onAddNode,
  onDeleteNode,
  onDeleteEdge,
  onAttachCondition,
  onRemoveCondition,
  onClearGraph,
  onSaveGraph,
  onBack,
  isGraphValid = false,
  isDraggingCondition = false,
  onValidate,
  isValidating = false,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<dia.Graph | null>(null);
  const paperRef = useRef<dia.Paper | null>(null);
  const { primaryHex } = useTheme();
  const primaryHexRef = useRef(primaryHex);
  primaryHexRef.current = primaryHex;

  const themeColors = useMemo(() => deriveThemeColors(primaryHex), [primaryHex]);

  const [showYamlDebug, setShowYamlDebug] = useState(false);
  const [paperTransform, setPaperTransform] = useState({ sx: 1, sy: 1, tx: 0, ty: 0 });
  const [isLocked, setIsLocked] = useState(false);

  // Selected edge for deletion
  const [selectedEdge, setSelectedEdge] = useState<{ source: string; target: string } | null>(null);

  // Stash callbacks in refs so the JointJS event closures always call the latest version
  const onNodeClickRef = useRef(onNodeClick);
  onNodeClickRef.current = onNodeClick;
  const onCancelConnectionRef = useRef(onCancelConnection);
  onCancelConnectionRef.current = onCancelConnection;
  const onDeleteEdgeRef = useRef(onDeleteEdge);
  onDeleteEdgeRef.current = onDeleteEdge;
  const setSelectedEdgeRef = useRef(setSelectedEdge);
  setSelectedEdgeRef.current = setSelectedEdge;

  // Track pointer start for click-vs-drag detection on JointJS elements
  const dragStartRef = useRef<{ x: number; y: number } | null>(null);

  // Previous state refs for diffing
  const prevNodesRef = useRef<CanvasNode[]>([]);
  const prevEdgesRef = useRef<CanvasEdge[]>([]);

  // ── Emit current paper transform to React state ─────────────────────

  const emitPaperTransform = useCallback(() => {
    const paper = paperRef.current;
    if (!paper) return;
    const s = paper.scale();
    const tr = paper.translate();
    safeFlushSync(() => setPaperTransform({ sx: s.sx, sy: s.sy, tx: tr.tx, ty: tr.ty }));
  }, []);

  // ── Initialize JointJS paper (once) ─────────────────────────────────

  useEffect(() => {
    if (!containerRef.current) return;

    const { graph, paper } = createJointPaper(containerRef.current, {
      interactive: { elementMove: true },
      showBackground: true,
    });
    graphRef.current = graph;
    paperRef.current = paper;

    const primaryNow = primaryHexRef.current || "#8b5cf6";
    injectSvgDefs(paper.el, primaryNow);
    injectStatusGlowFilters(paper.el);

    // ── Pan + Zoom (shared helper) ──
    const cleanupPanZoom = setupPanZoom(paper, (t) => {
      safeFlushSync(() => setPaperTransform(t));
    });

    // ── Click on blank → cancel connection + deselect edge ──
    paper.on("blank:pointerclick", () => {
      onCancelConnectionRef.current();
      setSelectedEdgeRef.current(null);
    });

    // ── Click-to-connect via JointJS events (allows drag to still work) ──
    paper.on("element:pointerdown", (_cellView: any, evt: any) => {
      const ne = evt.originalEvent ?? evt;
      dragStartRef.current = { x: ne.clientX, y: ne.clientY };
    });

    paper.on("element:pointerup", (cellView: any, evt: any) => {
      const start = dragStartRef.current;
      dragStartRef.current = null;
      if (!start) return;
      const ne = evt.originalEvent ?? evt;
      const dx = Math.abs(ne.clientX - start.x);
      const dy = Math.abs(ne.clientY - start.y);
      if (dx < CLICK_THRESHOLD && dy < CLICK_THRESHOLD) {
        setSelectedEdgeRef.current(null);
        onNodeClickRef.current(cellView.model.id as string);
      }
    });

    // ── Click on link → select it for deletion ──
    paper.on("link:pointerclick", (linkView: any) => {
      const model = linkView.model;
      const src = model.get("source")?.id;
      const tgt = model.get("target")?.id;
      if (src && tgt) {
        setSelectedEdgeRef.current({ source: src, target: tgt });
      }
    });

    // ── Element position change → trigger overlay re-render ──
    graph.on("change:position", () => {
      safeFlushSync(() => setPaperTransform((p) => ({ ...p })));
    });

    return () => {
      cleanupPanZoom();
      graph.off("change:position");
      paper.remove();
      graph.clear();
      graphRef.current = null;
      paperRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Lock/unlock node dragging ───────────────────────────────────────

  useEffect(() => {
    const paper = paperRef.current;
    if (!paper) return;
    paper.setInteractivity(isLocked ? false : { elementMove: true });
  }, [isLocked]);

  // ── Theme color update ──────────────────────────────────────────────

  useEffect(() => {
    const paper = paperRef.current;
    const graph = graphRef.current;
    if (!paper || !graph) return;
    const p = primaryHex || "#8b5cf6";
    injectSvgDefs(paper.el, p);
  }, [primaryHex]);

  // ── Sync canvasNodes → JointJS elements (add, remove, resize) ──────

  useEffect(() => {
    const graph = graphRef.current;
    if (!graph) return;

    const prevMap = new Map(prevNodesRef.current.map((n) => [n.id, n]));
    const currIds = new Set(canvasNodes.map((n) => n.id));

    for (const node of canvasNodes) {
      const refs = resolveConfigRefs(node.workspaceData?.config, allBlocks);
      const neededHeight = computeCreationNodeHeight(refs.length, node.conditions.length);
      const prevNode = prevMap.get(node.id);

      if (!prevNode) {
        createJointNode(graph, node.id, node.type, node.position, refs.length);
        const el = graph.getCell(node.id) as dia.Element | undefined;
        if (el) el.resize(NODE_WIDTH, neededHeight);
      } else {
        const el = graph.getCell(node.id) as dia.Element | undefined;
        if (el) {
          const curSize = el.size();
          if (Math.abs(curSize.height - neededHeight) > 1) {
            el.resize(NODE_WIDTH, neededHeight);
          }
        }
      }
    }

    for (const prev of prevNodesRef.current) {
      if (!currIds.has(prev.id)) {
        const el = graph.getCell(prev.id);
        if (el) el.remove();
      }
    }

    prevNodesRef.current = canvasNodes;
  }, [canvasNodes, allBlocks]);

  // ── Sync canvasEdges → JointJS links ────────────────────────────────

  useEffect(() => {
    const graph = graphRef.current;
    if (!graph) return;

    const prevEdgeKeys = new Set(prevEdgesRef.current.map((e) => e.id));
    const currEdgeKeys = new Set(canvasEdges.map((e) => e.id));

    const linkColor = (primaryHex || "#8b5cf6").startsWith("#")
      ? primaryHex || "#8b5cf6"
      : `#${primaryHex || "8b5cf6"}`;
    const colors = {
      primary: linkColor,
      bidi: themeColors.primaryLight,
      conditional: themeColors.conditionEdge,
    };

    for (const edge of canvasEdges) {
      if (!prevEdgeKeys.has(edge.id)) {
        createJointLink(graph, edge.id, edge.source, edge.target, colors, {
          isConditional: edge.isConditional,
          isBidirectional: edge.isBidirectional,
          branchLabel: edge.branch,
        });
      }
    }

    for (const prev of prevEdgesRef.current) {
      if (!currEdgeKeys.has(prev.id)) {
        const link = graph.getCell(prev.id);
        if (link) link.remove();
      }
    }

    prevEdgesRef.current = canvasEdges;
  }, [canvasEdges, primaryHex, themeColors.primaryLight, themeColors.conditionEdge]);

  // ── Highlight selected edge ─────────────────────────────────────────

  useEffect(() => {
    const graph = graphRef.current;
    if (!graph) return;
    for (const link of graph.getLinks()) {
      const src = link.get("source")?.id;
      const tgt = link.get("target")?.id;
      const isSelected =
        selectedEdge && src === selectedEdge.source && tgt === selectedEdge.target;
      if (isSelected) {
        link.attr("line/strokeWidth", 4);
        link.attr("line/opacity", 1);
      } else {
        const edge = canvasEdges.find((e) => e.id === link.id);
        link.attr("line/strokeWidth", edge?.isConditional ? 1.5 : edge?.isBidirectional ? 2.5 : 2);
        link.removeAttr("line/opacity");
      }
    }
  }, [selectedEdge, canvasEdges]);

  // ── Highlight connection source ─────────────────────────────────────

  useEffect(() => {
    const graph = graphRef.current;
    if (!graph) return;

    for (const el of graph.getElements()) {
      const isSource = el.id === connectionSource;
      el.attr("body/stroke", isSource ? SELECTED_STROKE : STATUS_STYLES.IDLE.stroke);
      el.attr("body/strokeWidth", isSource ? SELECTED_STROKE_WIDTH : STATUS_STYLES.IDLE.strokeWidth);
      if (isSource) {
        el.attr("body/strokeDasharray", "8 4");
      } else {
        el.removeAttr("body/strokeDasharray");
      }
    }
  }, [connectionSource, canvasNodes]);

  // ── Zoom controls ───────────────────────────────────────────────────

  const handleZoomIn = useCallback(() => {
    const paper = paperRef.current;
    if (!paper) return;
    const cur = paper.scale().sx;
    const ns = Math.min(MAX_ZOOM, cur * ZOOM_STEP);
    paper.scale(ns, ns);
    emitPaperTransform();
  }, [emitPaperTransform]);

  const handleZoomOut = useCallback(() => {
    const paper = paperRef.current;
    if (!paper) return;
    const cur = paper.scale().sx;
    const ns = Math.max(MIN_ZOOM, cur / ZOOM_STEP);
    paper.scale(ns, ns);
    emitPaperTransform();
  }, [emitPaperTransform]);

  const handleAutoFit = useCallback(() => {
    const paper = paperRef.current;
    const graph = graphRef.current;
    if (!paper || !graph || graph.getElements().length === 0) return;
    const container = containerRef.current;
    if (!container) return;
    const cw = container.clientWidth;
    const ch = container.clientHeight;
    if (cw < 50 || ch < 50) return;
    try {
      paper.scale(1, 1);
      paper.translate(0, 0);
      paper.setDimensions(cw, ch);
      paper.transformToFitContent(SCALE_CONTENT_TO_FIT_OPTS);
    } catch {
      return;
    }
    emitPaperTransform();
  }, [emitPaperTransform]);

  // ── Drag-and-drop from sidebar ──────────────────────────────────────

  const handleDragOver = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = isDraggingCondition ? "copy" : "move";
    },
    [isDraggingCondition],
  );

  const handleDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const paper = paperRef.current;
      if (!paper) return;

      const blockData = event.dataTransfer.getData("application/graphblock");
      if (!blockData) return;

      const block: BuildingBlock = JSON.parse(blockData);
      const isCondition = block.workspaceData?.category === "conditions";

      const rect = paper.el.getBoundingClientRect();
      const scale = paper.scale();
      const translate = paper.translate();
      const localX = (event.clientX - rect.left - translate.tx) / scale.sx;
      const localY = (event.clientY - rect.top - translate.ty) / scale.sy;

      if (isCondition) {
        const graph = graphRef.current;
        if (!graph) return;
        let targetNodeId: string | null = null;
        for (const el of graph.getElements()) {
          const bbox = el.getBBox();
          if (localX >= bbox.x && localX <= bbox.x + bbox.width && localY >= bbox.y && localY <= bbox.y + bbox.height) {
            targetNodeId = el.id as string;
            break;
          }
        }
        if (targetNodeId) {
          onAttachCondition(targetNodeId, block);
        }
        return;
      }

      onAddNode(block, { x: localX - NODE_WIDTH / 2, y: localY - 30 });
    },
    [onAddNode, onAttachCondition, isDraggingCondition],
  );

  // ── Delete selected edge ────────────────────────────────────────────

  const handleDeleteSelectedEdge = useCallback(() => {
    if (!selectedEdge) return;
    onDeleteEdge(selectedEdge.source, selectedEdge.target);
    setSelectedEdge(null);
  }, [selectedEdge, onDeleteEdge]);

  // ── Build overlay data from current JointJS positions ───────────────

  const overlayData = useMemo(() => {
    const graph = graphRef.current;
    if (!graph) return [] as OverlayNodeData[];

    return canvasNodes.map((node) => {
      const el = graph.getCell(node.id) as dia.Element | undefined;
      const pos = el ? el.position() : node.position;
      const refs = resolveConfigRefs(node.workspaceData?.config, allBlocks);
      const size = el ? el.size() : { width: NODE_WIDTH, height: NODE_HEADER_HEIGHT };
      return { ...node, x: pos.x, y: pos.y, width: size.width, height: size.height, refs };
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canvasNodes, allBlocks, paperTransform]);

  // ── JSX ─────────────────────────────────────────────────────────────

  return (
    <div className="flex-1 relative">
      <Card className="bg-background-card shadow-card border-gray-800 h-full">
        <GraphHeader
          onClearGraph={onClearGraph}
          onSaveGraph={onSaveGraph}
          onBack={onBack}
          isGraphValid={isGraphValid}
          onValidate={onValidate}
          isValidating={isValidating}
        />
        <CardContent className="p-0 h-full relative">
          {/* YAML Debug Panel */}
          {showYamlDebug && yamlFlow && (
            <div className="absolute top-4 right-4 z-50 bg-gray-900 border border-gray-700 rounded-lg p-4 max-w-md max-h-96 overflow-auto">
              <div className="flex justify-between items-center mb-2">
                <h3 className="text-sm font-medium text-white">YAML Flow State</h3>
                <button onClick={() => setShowYamlDebug(false)} className="text-gray-400 hover:text-white">&times;</button>
              </div>
              <pre className="text-xs text-gray-300 overflow-auto">
                {yaml.dump(yamlFlow, { indent: 2, lineWidth: -1 })}
              </pre>
            </div>
          )}

          {/* YAML Debug Toggle */}
          <button
            onClick={() => setShowYamlDebug(!showYamlDebug)}
            className="absolute top-4 right-4 z-40 bg-gray-800 hover:bg-gray-700 text-white px-3 py-1 text-xs rounded border border-gray-600"
          >
            {showYamlDebug ? "Hide" : "Show"} YAML
          </button>

          {/* Connection mode indicator */}
          {connectionSource && (
            <div className="absolute top-4 left-1/2 -translate-x-1/2 z-40 bg-blue-900/90 border border-blue-500/50 text-white px-4 py-2 rounded-lg text-sm flex items-center gap-2 shadow-lg">
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
              Click another node to connect &mdash;
              <button onClick={onCancelConnection} className="text-blue-300 hover:text-white underline text-xs">
                Cancel (Esc)
              </button>
            </div>
          )}

          {/* Selected edge toolbar */}
          {selectedEdge && (
            <div className="absolute top-4 left-1/2 -translate-x-1/2 z-40 bg-red-900/90 border border-red-500/50 text-white px-4 py-2 rounded-lg text-sm flex items-center gap-3 shadow-lg">
              <span>Edge selected</span>
              <Button
                variant="destructive"
                size="sm"
                className="h-7 px-3 text-xs"
                onClick={handleDeleteSelectedEdge}
              >
                <Trash2 className="w-3 h-3 mr-1" />
                Delete Edge
              </Button>
              <button
                onClick={() => setSelectedEdge(null)}
                className="text-red-300 hover:text-white text-xs underline"
              >
                Cancel
              </button>
            </div>
          )}

          <div className="h-full" style={{ height: "calc(100vh - 180px)" }}>
            {/* JointJS container */}
            <div ref={containerRef} className="h-full w-full" onDragOver={handleDragOver} onDrop={handleDrop} />

            {/* Zoom controls (bottom-right, raised above any status bars) */}
            <div className="absolute bottom-14 right-3 z-40 flex flex-col rounded-lg bg-black/70 backdrop-blur-sm">
              <button
                type="button"
                className="flex items-center justify-center w-8 h-8 text-white/80 hover:text-white hover:bg-white/10 rounded-t-lg transition-colors"
                onClick={handleZoomIn}
                aria-label="Zoom in"
                title="Zoom in"
              >
                <ZoomIn size={16} />
              </button>
              <button
                type="button"
                className="flex items-center justify-center w-8 h-8 text-white/80 hover:text-white hover:bg-white/10 transition-colors"
                onClick={handleZoomOut}
                aria-label="Zoom out"
                title="Zoom out"
              >
                <ZoomOut size={16} />
              </button>
              <button
                type="button"
                className="flex items-center justify-center w-8 h-8 text-white/80 hover:text-white hover:bg-white/10 transition-colors"
                onClick={handleAutoFit}
                aria-label="Fit to view"
                title="Fit to view"
              >
                <Maximize size={16} />
              </button>
              <button
                type="button"
                className={`flex items-center justify-center w-8 h-8 rounded-b-lg transition-colors ${
                  isLocked
                    ? "text-yellow-400 hover:text-yellow-300 bg-white/10"
                    : "text-white/80 hover:text-white hover:bg-white/10"
                }`}
                onClick={() => setIsLocked((prev) => !prev)}
                aria-label={isLocked ? "Unlock nodes" : "Lock nodes"}
                title={isLocked ? "Unlock node positions" : "Lock node positions"}
              >
                {isLocked ? <Lock size={16} /> : <Unlock size={16} />}
              </button>
            </div>

            {/* HTML overlays */}
            <div className="absolute inset-0 pointer-events-none" style={{ overflow: "hidden" }}>
              <div
                style={{
                  transformOrigin: "0 0",
                  transform: `matrix(${paperTransform.sx}, 0, 0, ${paperTransform.sy}, ${paperTransform.tx}, ${paperTransform.ty})`,
                }}
              >
                {overlayData.map((node) => (
                  <CreationNodeOverlay
                    key={node.id}
                    node={node}
                    refs={node.refs}
                    x={node.x}
                    y={node.y}
                    width={node.width}
                    nodeHeight={node.height}
                    isConnectionSource={node.id === connectionSource}
                    connectionSourceActive={connectionSource !== null}
                    scale={paperTransform.sx}
                    onDeleteNode={onDeleteNode}
                    onRemoveCondition={onRemoveCondition}
                    themeColors={themeColors}
                  />
                ))}
              </div>
            </div>

            {/* Empty state */}
            {canvasNodes.length <= 2 && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="text-center">
                  <Plus className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                  <h3 className="mt-2 text-sm font-medium text-gray-300">No nodes yet</h3>
                  <p className="mt-1 text-sm text-gray-400">Drag building blocks from the sidebar to get started</p>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Internal overlay data type
// ---------------------------------------------------------------------------

interface OverlayNodeData extends CanvasNode {
  x: number;
  y: number;
  width: number;
  height: number;
  refs: ResolvedRef[];
}

// ---------------------------------------------------------------------------
// Creation node overlay
// ---------------------------------------------------------------------------

interface CreationNodeOverlayProps {
  node: CanvasNode;
  refs: ResolvedRef[];
  x: number;
  y: number;
  width: number;
  nodeHeight: number;
  isConnectionSource: boolean;
  connectionSourceActive: boolean;
  scale: number;
  onDeleteNode: (nodeId: string) => void;
  onRemoveCondition: (nodeId: string, conditionRid: string) => void;
  themeColors: ReturnType<typeof deriveThemeColors>;
}

function CreationNodeOverlay({
  node,
  refs,
  x,
  y,
  width,
  nodeHeight,
  isConnectionSource,
  connectionSourceActive,
  scale,
  onDeleteNode,
  onRemoveCondition,
  themeColors,
}: CreationNodeOverlayProps) {
  const isProtected = node.id === "user_input" || node.id === "finalize";
  const icon = nodeIconForType(node.type);
  const hasSubElements = refs.length > 0;

  return (
    <div
      className="absolute"
      style={{ left: x, top: y, width, height: nodeHeight, pointerEvents: "none" }}
    >
      {/* Connection source visual indicator */}
      {isConnectionSource && (
        <div
          className="absolute inset-0 rounded-xl"
          style={{ border: `2px dashed ${SELECTED_STROKE}`, pointerEvents: "none" }}
        />
      )}
      {connectionSourceActive && !isConnectionSource && (
        <div
          className="absolute inset-0 rounded-xl"
          style={{ border: "2px solid rgba(96, 165, 250, 0.25)", pointerEvents: "none" }}
        />
      )}

      {/* Header */}
      <div
        className="flex items-center gap-2 px-3"
        style={{
          height: NODE_HEADER_HEIGHT,
          borderBottom: hasSubElements || node.conditions.length > 0
            ? "1px solid rgba(255,255,255,0.12)"
            : "none",
        }}
      >
        <span
          className="flex items-center justify-center rounded-full"
          style={{
            width: Math.max(20 / scale, 26),
            height: Math.max(20 / scale, 26),
            background: "rgba(255,255,255,0.25)",
            fontSize: Math.max(12 / scale, 14),
            flexShrink: 0,
          }}
        >
          {icon}
        </span>
        <span
          className="text-white font-semibold truncate flex-1"
          style={{
            fontSize: Math.max(9 / scale, 12),
            fontFamily: "system-ui, -apple-system, sans-serif",
          }}
        >
          {node.label}
        </span>

        {!isProtected && (
          <button
            className="w-5 h-5 flex items-center justify-center text-gray-500 hover:text-red-400 transition-colors rounded"
            style={{ pointerEvents: "auto" }}
            onClick={(e) => { e.stopPropagation(); onDeleteNode(node.id); }}
            title="Delete node"
          >
            <X className="w-3 h-3" />
          </button>
        )}
      </div>

      {/* Sub-element badges */}
      {hasSubElements && (
        <div style={{ padding: `${NODE_BODY_PADDING}px` }}>
          {refs.map((ref, i) => {
            const category = CATEGORY_TYPE_TO_PLURAL[ref.type] || ref.category || "default";
            const display = getCategoryDisplay(category);
            return (
              <div
                key={`${ref.id}-${i}`}
                className="flex items-center rounded-full border"
                style={{
                  height: ELEMENT_BADGE_HEIGHT,
                  marginTop: i > 0 ? ELEMENT_GAP : 0,
                  background: BADGE_BG,
                  borderColor: BADGE_BORDER,
                  backdropFilter: "blur(6px)",
                  fontSize: Math.max(9 / scale, 11),
                  paddingLeft: 4,
                  paddingRight: 8,
                  gap: 5,
                }}
              >
                <span className="flex-shrink-0 flex items-center justify-center text-white [&>svg]:w-3.5 [&>svg]:h-3.5">
                  {display.icon}
                </span>
                <span
                  className="truncate"
                  style={{ color: "rgba(255,255,255,0.88)", fontWeight: 500, letterSpacing: "0.01em" }}
                >
                  {ref.name}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Conditions (inside the node card) */}
      {node.conditions.length > 0 && (
        <div style={{ padding: `${NODE_BODY_PADDING}px` }}>
          {node.conditions.map((condition) => (
            <div
              key={condition.id}
              className="flex items-center gap-1.5 px-2 py-1 rounded text-xs"
              style={{
                backgroundColor: themeColors.conditionCardBg,
                border: `1px solid ${themeColors.conditionCardBorder}`,
              }}
            >
              <GitBranch className="w-3 h-3 flex-shrink-0" style={{ color: themeColors.conditionAccent }} />
              <span className="text-white truncate flex-1 text-[10px]">{condition.label}</span>
              <button
                className="w-4 h-4 flex items-center justify-center text-red-400 hover:text-red-300"
                style={{ pointerEvents: "auto" }}
                onClick={(e) => {
                  e.stopPropagation();
                  onRemoveCondition(node.id, condition.workspaceData?.rid || condition.id);
                }}
              >
                <Trash2 className="w-2.5 h-2.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default GraphCanvas;
