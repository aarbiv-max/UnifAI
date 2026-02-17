import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { useToast } from "@/hooks/use-toast";
import { CurrentGraph, BuildingBlock, CanvasNode, CanvasEdge } from "@/types/graph";
import { getCategoryDisplay, isOrchestratorType } from "@/components/shared/helpers";
import { useAuth } from "@/contexts/AuthContext";
import { useTheme } from "@/contexts/ThemeContext";
import { deriveThemeColors } from "@/lib/colorUtils";
import axios from "../http/axiosAgentConfig";
import * as yaml from "js-yaml";
import { saveBlueprint } from "@/api/blueprints";
import type { EdgeDirection } from "@/components/agentic-ai/graphs/EdgeDirectionModal";

// ---------------------------------------------------------------------------
// YAML flow types
// ---------------------------------------------------------------------------

interface YamlFlowNode {
  rid: string;
  name: string;
  type?: string;
  config?: any;
}

interface YamlFlowPlanStep {
  uid: string;
  node: string;
  after?: string | string[] | null;
  branches?: any;
  exit_condition?: string;
}

interface YamlFlowCondition {
  rid: string;
  name: string;
  type?: string;
  config?: any;
}

interface YamlFlowState {
  name?: string;
  description?: string;
  nodes: YamlFlowNode[];
  plan: YamlFlowPlanStep[];
  conditions?: YamlFlowCondition[];
}

const defaultYmlState: YamlFlowState = {
  nodes: [
    {
      rid: "user_question",
      name: "User Question Node",
      type: "user_question_node",
      config: { type: "user_question_node" },
    },
    {
      rid: "final_answer",
      name: "Final Answer Node",
      type: "final_answer_node",
      config: { type: "final_answer_node" },
    },
  ],
  plan: [
    { uid: "user_input", node: "user_question" },
    { uid: "finalize", node: "final_answer" },
  ],
};

// ---------------------------------------------------------------------------
// Default canvas nodes (always present)
// ---------------------------------------------------------------------------

const DEFAULT_USER_INPUT: CanvasNode = {
  id: "user_input",
  label: "User Input",
  position: { x: 200, y: 80 },
  type: "user_question_node",
  color: "#4A90E2",
  workspaceData: {
    rid: "user_question",
    name: "user_question",
    category: "nodes",
    type: "user_question_node",
    config: { name: "User Input", type: "user_question_node" },
    version: 1,
    created: "",
    updated: "",
    nested_refs: [],
  },
  conditions: [],
};

const DEFAULT_FINAL_ANSWER: CanvasNode = {
  id: "finalize",
  label: "Final Answer",
  position: { x: 200, y: 600 },
  type: "final_answer_node",
  color: "#50C878",
  workspaceData: {
    rid: "final_answer",
    name: "final_answer",
    category: "nodes",
    type: "final_answer_node",
    config: { name: "Final Answer", type: "final_answer_node" },
    version: 1,
    created: "",
    updated: "",
    nested_refs: [],
  },
  conditions: [],
};

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export interface SavedBlueprintInfo {
  blueprintId: string;
  name: string;
  description: string;
}

interface UseGraphLogicOptions {
  onSaveComplete?: (savedBlueprint?: SavedBlueprintInfo) => void;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export const useGraphLogic = (options: UseGraphLogicOptions = {}) => {
  const { onSaveComplete } = options;
  const { toast } = useToast();
  const { primaryHex } = useTheme();
  const { user } = useAuth();
  const USER_ID = user?.username || "default";

  const themeColors = useMemo(() => deriveThemeColors(primaryHex), [primaryHex]);

  // ── Canvas node / edge state ────────────────────────────────────────
  const [canvasNodes, setCanvasNodes] = useState<CanvasNode[]>([
    { ...DEFAULT_USER_INPUT },
    { ...DEFAULT_FINAL_ANSWER },
  ]);
  const [canvasEdges, setCanvasEdges] = useState<CanvasEdge[]>([]);
  const nodeIdCounter = useRef(3);

  // ── Building blocks state ───────────────────────────────────────────
  const [buildingBlocksData, setBuildingBlocksData] = useState<BuildingBlock[]>([]);
  const [orchestratorsData, setOrchestratorsData] = useState<BuildingBlock[]>([]);
  const [conditionsData, setConditionsData] = useState<BuildingBlock[]>([]);
  const [allBlocksData, setAllBlocksData] = useState<BuildingBlock[]>([]);
  const [isLoadingBlocks, setIsLoadingBlocks] = useState(true);

  // ── Edge direction modal ────────────────────────────────────────────
  const [edgeDirectionModal, setEdgeDirectionModal] = useState({
    isOpen: false,
    sourceNodeId: "",
    targetNodeId: "",
  });

  // ── Conditional edge modal state ────────────────────────────────────
  const [conditionalEdgeModal, setConditionalEdgeModal] = useState({
    isOpen: false,
    sourceNodeId: "",
    targetNodeId: "",
    conditionType: "",
    existingBranches: [] as string[],
  });

  // ── Connection source tracking (click-to-connect) ──────────────────
  const [connectionSource, setConnectionSource] = useState<string | null>(null);

  // ── YAML flow ───────────────────────────────────────────────────────
  const [yamlFlow, setYamlFlow] = useState<YamlFlowState>({ ...defaultYmlState });

  // ── Validation state ────────────────────────────────────────────────
  const [isGraphValid, setIsGraphValid] = useState(false);
  const [validationResult, setValidationResult] = useState<any>(null);
  const [fixSuggestions, setFixSuggestions] = useState<any[]>([]);
  const [isValidating, setIsValidating] = useState(false);

  // ── Save state ──────────────────────────────────────────────────────
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // ── Pending bidirectional edges (queued while conditional modals resolve)
  const pendingBidiRef = useRef<{ source: string; target: string } | null>(null);

  // ── Current graph metadata ──────────────────────────────────────────
  const [currentGraph, setCurrentGraph] = useState<CurrentGraph>({
    id: `graph-${Date.now()}`,
    name: "Untitled Graph",
    nodes: [],
    edges: [],
    metadata: {
      created: new Date(),
      lastModified: new Date(),
      nodeCount: 2,
      edgeCount: 0,
    },
  });

  // ── Drag state ──────────────────────────────────────────────────────
  const [isDraggingCondition, setIsDraggingCondition] = useState(false);

  // =====================================================================
  // Building blocks loading
  // =====================================================================

  const transformResourceToBlock = (resource: any): BuildingBlock => {
    const display = getCategoryDisplay(resource.category);
    return {
      id: resource.rid,
      type: resource.type,
      label: resource.name,
      color: display.color,
      description: `${resource.category}/${resource.type} - ${resource.name}`,
      workspaceData: {
        rid: resource.rid,
        name: resource.name,
        category: resource.category,
        type: resource.type,
        config: resource.cfg_dict,
        version: resource.version,
        created: resource.created,
        updated: resource.updated,
        nested_refs: resource.nested_refs,
      },
    };
  };

  const loadBuildingBlocks = useCallback(async () => {
    try {
      setIsLoadingBlocks(true);
      const response = await axios.get(
        `/resources/resources.list?userId=${USER_ID}`,
      );
      const allBlocks: BuildingBlock[] = response.data.resources.map(transformResourceToBlock);
      setAllBlocksData(allBlocks);

      const nodeBlocks = allBlocks
        .filter(
          (b) =>
            b.workspaceData?.category === "nodes" &&
            !isOrchestratorType(b.workspaceData?.type || ""),
        )
        .sort((a, b) => a.label.localeCompare(b.label));

      const orchestratorBlocks = allBlocks
        .filter(
          (b) =>
            b.workspaceData?.category === "nodes" &&
            isOrchestratorType(b.workspaceData?.type || ""),
        )
        .sort((a, b) => a.label.localeCompare(b.label));

      const conditionBlocks = allBlocks
        .filter((b) => b.workspaceData?.category === "conditions")
        .sort((a, b) => a.label.localeCompare(b.label));

      setBuildingBlocksData(nodeBlocks);
      setOrchestratorsData(orchestratorBlocks);
      setConditionsData(conditionBlocks);
    } catch (error) {
      console.error("Error loading workspace resources:", error);
      toast({
        title: "Error Loading Resources",
        description: "Failed to load workspace resources from server",
        variant: "destructive",
      });
    } finally {
      setIsLoadingBlocks(false);
    }
  }, [toast]);

  useEffect(() => {
    loadBuildingBlocks();
  }, [loadBuildingBlocks]);

  // =====================================================================
  // Validation
  // =====================================================================

  const validateGraph = useCallback(async () => {
    if (canvasNodes.length <= 2) {
      setIsGraphValid(false);
      setValidationResult(null);
      setFixSuggestions([]);
      return;
    }
    try {
      setIsValidating(true);
      const yamlFlowForValidation = {
        name: yamlFlow.name || "Untitled blueprint",
        description: yamlFlow.description || "default",
        conditions: yamlFlow.conditions || [],
        nodes: yamlFlow.nodes || [],
        plan: yamlFlow.plan || [],
      };
      const yamlString = yaml.dump(yamlFlowForValidation, {
        indent: 2,
        lineWidth: -1,
        noRefs: true,
        sortKeys: false,
      });
      const response = await axios.post(
        "/graph/validation/all.validate",
        yamlString,
        { headers: { "Content-Type": "text/plain" } },
      );
      const { validation_result, fix_suggestions } = response.data;
      setValidationResult(validation_result);
      setFixSuggestions(fix_suggestions || []);
      setIsGraphValid(validation_result?.is_valid || false);
    } catch (error: any) {
      console.error("Error validating graph:", error);
      const statusCode = error?.response?.status;
      const detail = error?.response?.data?.detail || error?.message || "Unknown error";
      setIsGraphValid(false);
      setValidationResult(null);
      setFixSuggestions([]);
      toast({
        title: "Validation Error",
        description: statusCode
          ? `Server returned ${statusCode}: ${detail}`
          : `Could not reach validation service: ${detail}`,
        variant: "destructive",
      });
    } finally {
      setIsValidating(false);
    }
  }, [yamlFlow, canvasNodes.length, toast]);

  useEffect(() => {
    if (yamlFlow.plan && yamlFlow.plan.length > 2) {
      const t = setTimeout(() => validateGraph(), 500);
      return () => clearTimeout(t);
    }
  }, [yamlFlow, validateGraph]);

  // =====================================================================
  // Node operations
  // =====================================================================

  const addNode = useCallback(
    (block: BuildingBlock, position: { x: number; y: number }) => {
      const nodeUid = `${block.workspaceData?.name || block.label}-${block.workspaceData?.rid || block.id}-${nodeIdCounter.current}`;
      nodeIdCounter.current += 1;

      const newNode: CanvasNode = {
        id: nodeUid,
        label: block.label,
        position,
        type: block.workspaceData?.type || block.type,
        color: block.color,
        workspaceData: block.workspaceData,
        conditions: [],
      };

      setCanvasNodes((prev) => [...prev, newNode]);

      setYamlFlow((prev) => {
        const nodeRid = `$ref:${block.workspaceData?.rid || block.id}`;
        const nodeExists = prev.nodes.some((n) => n.rid === nodeRid);
        const newYamlNode: Record<string, unknown> = {
          rid: nodeRid,
          name: block.workspaceData?.name || block.label,
        };
        const newPlanStep = {
          uid: nodeUid,
          node: block.workspaceData?.rid || block.id,
        };
        return {
          ...prev,
          nodes: nodeExists ? prev.nodes : [...prev.nodes, newYamlNode],
          plan: [...prev.plan, newPlanStep],
        };
      });

      return nodeUid;
    },
    [],
  );

  const deleteNode = useCallback(
    (nodeId: string) => {
      if (nodeId === "user_input" || nodeId === "finalize") {
        toast({
          title: "Cannot Delete Required Node",
          description: "User Input and Final Answer nodes are required and cannot be deleted",
          variant: "destructive",
        });
        return;
      }

      setCanvasNodes((prev) => prev.filter((n) => n.id !== nodeId));
      setCanvasEdges((prev) =>
        prev.filter((e) => e.source !== nodeId && e.target !== nodeId),
      );

      setYamlFlow((prev) => {
        const updatedPlan = prev.plan
          .filter((step) => step.uid !== nodeId)
          .map((step) => {
            if (step.after === nodeId) {
              const { after, ...rest } = step;
              return rest;
            }
            if (Array.isArray(step.after)) {
              const filtered = step.after.filter((a) => a !== nodeId);
              if (filtered.length === 0) {
                const { after, ...rest } = step;
                return rest;
              }
              return { ...step, after: filtered.length === 1 ? filtered[0] : filtered };
            }
            return step;
          });
        return { ...prev, plan: updatedPlan };
      });

      if (connectionSource === nodeId) setConnectionSource(null);
    },
    [toast, connectionSource],
  );

  // =====================================================================
  // Edge operations
  // =====================================================================

  const addEdgeInternal = useCallback(
    (sourceId: string, targetId: string, isConditional = false, branch?: string, isBidirectional = false) => {
      const edgeId = `edge-${sourceId}-${targetId}-${branch || Date.now()}`;
      const newEdge: CanvasEdge = {
        id: edgeId,
        source: sourceId,
        target: targetId,
        isConditional,
        isBidirectional,
        branch,
      };

      setCanvasEdges((prev) => {
        const exists = prev.some(
          (e) => e.source === sourceId && e.target === targetId && !e.branch && !branch,
        );
        if (exists) return prev;
        return [...prev, newEdge];
      });

      if (!isConditional) {
        setYamlFlow((prev) => {
          const updatedPlan = prev.plan.map((step) => {
            if (step.uid !== targetId) return step;
            const existing = step.after;
            let newAfter: string | string[];
            if (!existing) {
              newAfter = sourceId;
            } else if (Array.isArray(existing)) {
              newAfter = existing.includes(sourceId) ? existing : [...existing, sourceId];
            } else {
              newAfter = existing === sourceId ? existing : [existing, sourceId];
            }
            return { ...step, after: newAfter };
          });
          return { ...prev, plan: updatedPlan };
        });
      }
    },
    [],
  );

  const deleteEdge = useCallback(
    (sourceId: string, targetId: string) => {
      setCanvasEdges((prev) =>
        prev.filter((e) => !(e.source === sourceId && e.target === targetId)),
      );

      setYamlFlow((prev) => {
        const updatedPlan = prev.plan.map((step) => {
          if (step.uid === targetId) {
            if (step.after) {
              if (Array.isArray(step.after)) {
                const filtered = step.after.filter((a) => a !== sourceId);
                if (filtered.length === 0) {
                  const { after, ...rest } = step;
                  return rest;
                }
                return { ...step, after: filtered.length === 1 ? filtered[0] : filtered };
              }
              if (step.after === sourceId) {
                const { after, ...rest } = step;
                return rest;
              }
            }
            if (step.branches) {
              const updatedBranches = { ...step.branches };
              Object.keys(updatedBranches).forEach((key) => {
                if (updatedBranches[key] === targetId) delete updatedBranches[key];
              });
              if (Object.keys(updatedBranches).length === 0) {
                const { branches, ...rest } = step;
                return rest;
              }
              return { ...step, branches: updatedBranches };
            }
          }
          return step;
        });
        return { ...prev, plan: updatedPlan };
      });
    },
    [],
  );

  // =====================================================================
  // Click-to-connect flow
  // =====================================================================

  const handleNodeClick = useCallback(
    (nodeId: string) => {
      if (!connectionSource) {
        setConnectionSource(nodeId);
        return;
      }

      if (connectionSource === nodeId) {
        setConnectionSource(null);
        return;
      }

      const sourceNode = canvasNodes.find((n) => n.id === connectionSource);
      const targetNode = canvasNodes.find((n) => n.id === nodeId);
      if (!sourceNode || !targetNode) {
        setConnectionSource(null);
        return;
      }

      setEdgeDirectionModal({
        isOpen: true,
        sourceNodeId: connectionSource,
        targetNodeId: nodeId,
      });
    },
    [connectionSource, canvasNodes],
  );

  const cancelConnection = useCallback(() => {
    setConnectionSource(null);
  }, []);

  // ── Remove existing edges between a pair of nodes ───────────────────

  const removeEdgesBetween = useCallback(
    (nodeA: string, nodeB: string) => {
      setCanvasEdges((prev) =>
        prev.filter(
          (e) =>
            !((e.source === nodeA && e.target === nodeB) ||
              (e.source === nodeB && e.target === nodeA)),
        ),
      );

      setYamlFlow((prev) => {
        const updatedPlan = prev.plan.map((step) => {
          if (step.uid === nodeB && step.after) {
            if (Array.isArray(step.after)) {
              const filtered = step.after.filter((a) => a !== nodeA);
              if (filtered.length === 0) {
                const { after, ...rest } = step;
                return rest;
              }
              return { ...step, after: filtered.length === 1 ? filtered[0] : filtered };
            }
            if (step.after === nodeA) {
              const { after, ...rest } = step;
              return rest;
            }
          }
          if (step.uid === nodeA && step.after) {
            if (Array.isArray(step.after)) {
              const filtered = step.after.filter((a) => a !== nodeB);
              if (filtered.length === 0) {
                const { after, ...rest } = step;
                return rest;
              }
              return { ...step, after: filtered.length === 1 ? filtered[0] : filtered };
            }
            if (step.after === nodeB) {
              const { after, ...rest } = step;
              return rest;
            }
          }
          return step;
        });
        return { ...prev, plan: updatedPlan };
      });
    },
    [],
  );

  // ── Handle edge direction choice ────────────────────────────────────

  const handleEdgeDirectionConfirm = useCallback(
    (direction: EdgeDirection) => {
      const { sourceNodeId, targetNodeId } = edgeDirectionModal;
      setEdgeDirectionModal({ isOpen: false, sourceNodeId: "", targetNodeId: "" });
      setConnectionSource(null);

      // Remove any existing edges between these two nodes first
      removeEdgesBetween(sourceNodeId, targetNodeId);

      const sourceNode = canvasNodes.find((n) => n.id === sourceNodeId);
      const hasCondition = sourceNode && sourceNode.conditions.length > 0;

      if (hasCondition) {
        const condition = sourceNode.conditions[0];
        const conditionType = condition.workspaceData?.type || condition.type;
        const otherEdges = canvasEdges.filter(
          (e) => e.source === sourceNodeId && e.target !== targetNodeId,
        );
        const existingBranches = otherEdges
          .map((e) => e.branch)
          .filter(Boolean) as string[];

        if (direction === "bidirectional") {
          pendingBidiRef.current = { source: targetNodeId, target: sourceNodeId };
        }

        setConditionalEdgeModal({
          isOpen: true,
          sourceNodeId,
          targetNodeId,
          conditionType,
          existingBranches,
        });
        return;
      }

      addEdgeInternal(sourceNodeId, targetNodeId, false, undefined, direction === "bidirectional");

      if (direction === "bidirectional") {
        const targetNode = canvasNodes.find((n) => n.id === targetNodeId);
        const targetHasCondition = targetNode && targetNode.conditions.length > 0;
        if (targetHasCondition) {
          const condition = targetNode.conditions[0];
          const conditionType = condition.workspaceData?.type || condition.type;
          const otherEdges = canvasEdges.filter(
            (e) => e.source === targetNodeId && e.target !== sourceNodeId,
          );
          const existingBranches = otherEdges
            .map((e) => e.branch)
            .filter(Boolean) as string[];
          setConditionalEdgeModal({
            isOpen: true,
            sourceNodeId: targetNodeId,
            targetNodeId: sourceNodeId,
            conditionType,
            existingBranches,
          });
        } else {
          addEdgeInternal(targetNodeId, sourceNodeId, false, undefined, true);
        }
      }
    },
    [edgeDirectionModal, canvasNodes, canvasEdges, addEdgeInternal, removeEdgesBetween],
  );

  const handleEdgeDirectionCancel = useCallback(() => {
    setEdgeDirectionModal({ isOpen: false, sourceNodeId: "", targetNodeId: "" });
    setConnectionSource(null);
  }, []);

  // =====================================================================
  // Conditional edge handling
  // =====================================================================

  const createConditionalEdge = useCallback(
    (sourceId: string, targetId: string, branchConfig: any) => {
      const edgeId = `edge-${sourceId}-${targetId}-${branchConfig.branch || Date.now()}`;

      const newEdge: CanvasEdge = {
        id: edgeId,
        source: sourceId,
        target: targetId,
        isConditional: true,
        branch: branchConfig.branch || "",
      };

      setCanvasEdges((prev) => [...prev, newEdge]);

      const sourceNode = canvasNodes.find((n) => n.id === sourceId);
      const condition = sourceNode?.conditions?.[0];

      setYamlFlow((prev) => {
        const updatedPlan = prev.plan.map((step) => {
          if (step.uid === sourceId && condition) {
            const existingBranches = step.branches || {};
            let newBranches = { ...existingBranches };
            if (branchConfig.conditionType === "router_direct") {
              newBranches[targetId] = targetId;
            } else if (branchConfig.conditionType === "router_boolean") {
              let branchKey =
                branchConfig.branch === "true"
                  ? true
                  : branchConfig.branch === "false"
                    ? false
                    : branchConfig.branch;
              newBranches[branchKey as any] = targetId;
            }
            return {
              ...step,
              exit_condition: condition.workspaceData?.rid || condition.id,
              branches: newBranches,
            };
          }
          return step;
        });

        const conditionRid = condition?.workspaceData?.rid || condition?.id;
        const conditionExists = (prev.conditions || []).some(
          (c: any) => c.rid === `$ref:${conditionRid}`,
        );
        let updatedConditions = prev.conditions || [];
        if (condition && !conditionExists) {
          updatedConditions = [
            ...updatedConditions,
            {
              rid: `$ref:${conditionRid}`,
              name: condition.workspaceData?.name || condition.label,
            },
          ];
        }
        return {
          ...prev,
          conditions: updatedConditions.length > 0 ? updatedConditions : [],
          plan: updatedPlan,
        };
      });
    },
    [canvasNodes],
  );

  const handleConditionalEdgeConfirm = useCallback(
    (branchConfig: any) => {
      const { sourceNodeId, targetNodeId, conditionType } = conditionalEdgeModal;

      createConditionalEdge(sourceNodeId, targetNodeId, {
        ...branchConfig,
        conditionType,
      });

      setConditionalEdgeModal({
        isOpen: false,
        sourceNodeId: "",
        targetNodeId: "",
        conditionType: "",
        existingBranches: [],
      });

      if (pendingBidiRef.current) {
        const { source, target } = pendingBidiRef.current;
        pendingBidiRef.current = null;
        const reverseSource = canvasNodes.find((n) => n.id === source);
        const reverseHasCondition = reverseSource && reverseSource.conditions.length > 0;
        if (reverseHasCondition) {
          const condition = reverseSource.conditions[0];
          const conditionType = condition.workspaceData?.type || condition.type;
          const existingEdges = canvasEdges.filter((e) => e.source === source);
          const existingBranches = existingEdges
            .map((e) => e.branch)
            .filter(Boolean) as string[];
          setConditionalEdgeModal({
            isOpen: true,
            sourceNodeId: source,
            targetNodeId: target,
            conditionType,
            existingBranches,
          });
        } else {
          addEdgeInternal(source, target);
        }
      }
    },
    [conditionalEdgeModal, createConditionalEdge, canvasNodes, canvasEdges, addEdgeInternal],
  );

  const handleConditionalEdgeCancel = useCallback(() => {
    pendingBidiRef.current = null;
    setConditionalEdgeModal({
      isOpen: false,
      sourceNodeId: "",
      targetNodeId: "",
      conditionType: "",
      existingBranches: [],
    });
  }, []);

  // =====================================================================
  // Condition attachment
  // =====================================================================

  const attachConditionToNode = useCallback(
    (nodeId: string, condition: BuildingBlock) => {
      const targetNode = canvasNodes.find((n) => n.id === nodeId);
      if (targetNode && targetNode.conditions.length > 0) {
        toast({
          title: "Condition Limit Reached",
          description:
            "Each node can only have one condition attached. Remove the existing condition first.",
          variant: "destructive",
        });
        return;
      }

      setCanvasNodes((prev) =>
        prev.map((n) =>
          n.id === nodeId ? { ...n, conditions: [condition] } : n,
        ),
      );

      setYamlFlow((prev) => {
        const conditionRid = condition.workspaceData?.rid || condition.id;
        const updatedPlan = prev.plan.map((step) =>
          step.uid === nodeId
            ? { ...step, exit_condition: conditionRid }
            : step,
        );
        const conditionExists = (prev.conditions || []).some(
          (c: any) => c.rid === `$ref:${conditionRid}`,
        );
        let updatedConditions = prev.conditions || [];
        if (!conditionExists) {
          updatedConditions = [
            ...updatedConditions,
            {
              rid: `$ref:${conditionRid}`,
              name: condition.workspaceData?.name || condition.label,
            },
          ];
        }
        return { ...prev, conditions: updatedConditions, plan: updatedPlan };
      });
    },
    [canvasNodes, toast],
  );

  const removeConditionFromNode = useCallback(
    (nodeId: string, conditionRid: string) => {
      setCanvasNodes((prev) =>
        prev.map((n) =>
          n.id === nodeId
            ? {
                ...n,
                conditions: n.conditions.filter(
                  (c) => (c.workspaceData?.rid || c.id) !== conditionRid,
                ),
              }
            : n,
        ),
      );
      setCanvasEdges((prev) => prev.filter((e) => e.source !== nodeId));

      setYamlFlow((prev) => {
        const updatedPlan = prev.plan.map((step) => {
          if (step.uid === nodeId && step.exit_condition === conditionRid) {
            const { exit_condition, branches, ...rest } = step;
            return rest;
          }
          return step;
        });
        const updatedConditions = (prev.conditions || []).filter(
          (c: any) => c.rid !== `$ref:${conditionRid}`,
        );
        return {
          ...prev,
          conditions: updatedConditions.length > 0 ? updatedConditions : [],
          plan: updatedPlan,
        };
      });
    },
    [],
  );

  // =====================================================================
  // Drag-and-drop from sidebar
  // =====================================================================

  const onDragStart = useCallback(
    (event: React.DragEvent, block: BuildingBlock) => {
      const blockData = {
        id: block.id,
        type: block.type,
        label: block.label,
        description: block.description,
        color: block.color,
        workspaceData: block.workspaceData,
      };
      event.dataTransfer.setData("application/graphblock", JSON.stringify(blockData));

      const isCondition = block.workspaceData?.category === "conditions";
      setIsDraggingCondition(isCondition);
      event.dataTransfer.effectAllowed = isCondition ? "copy" : "move";

      const previewColor = themeColors.primary;
      const dragPreview = document.createElement("div");
      dragPreview.style.cssText = `
        position: absolute; top: -1000px; left: -1000px;
        padding: 8px 12px; background: ${previewColor}; color: white;
        border-radius: 6px; font-size: 14px; font-weight: 500;
        white-space: nowrap; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        pointer-events: none; z-index: 1000;
      `;
      dragPreview.textContent = block.label;
      document.body.appendChild(dragPreview);
      event.dataTransfer.setDragImage(dragPreview, 50, 20);
      setTimeout(() => {
        if (document.body.contains(dragPreview)) document.body.removeChild(dragPreview);
      }, 0);
    },
    [themeColors.primary],
  );

  const onDragEnd = useCallback(() => {
    setIsDraggingCondition(false);
  }, []);

  // =====================================================================
  // Clear graph
  // =====================================================================

  const clearGraph = useCallback(() => {
    setCanvasNodes([{ ...DEFAULT_USER_INPUT }, { ...DEFAULT_FINAL_ANSWER }]);
    setCanvasEdges([]);
    setYamlFlow({ ...defaultYmlState });
    setConnectionSource(null);
    setIsGraphValid(false);
    setValidationResult(null);
    setFixSuggestions([]);
    nodeIdCounter.current = 3;
  }, []);

  // =====================================================================
  // Save
  // =====================================================================

  const openSaveModal = useCallback(() => {
    if (!isGraphValid) {
      toast({
        title: "Cannot Save Invalid Graph",
        description: "Please fix all validation issues before saving the graph.",
        variant: "destructive",
      });
      return;
    }
    setSaveModalOpen(true);
  }, [isGraphValid, toast]);

  const saveGraph = useCallback(
    async (name: string, description: string) => {
      try {
        setIsSaving(true);
        const updatedYamlFlow = { ...yamlFlow, name, description };
        setYamlFlow(updatedYamlFlow);
        const yamlString = yaml.dump(updatedYamlFlow, {
          indent: 2,
          lineWidth: -1,
          noRefs: true,
          sortKeys: false,
        });
        const response = await saveBlueprint(yamlString, USER_ID);
        if (response.status === "success") {
          toast({
            title: "Blueprint Saved Successfully",
            description: `Blueprint "${name}" saved successfully`,
            variant: "default",
          });
          setSaveModalOpen(false);
          setIsSaving(false);
          if (onSaveComplete) {
            setTimeout(
              () =>
                onSaveComplete({
                  blueprintId: response.blueprint_id,
                  name,
                  description,
                }),
              100,
            );
          }
        } else {
          throw new Error("Unknown error occurred while saving blueprint");
        }
      } catch (error) {
        console.error("Error saving graph:", error);
        toast({
          title: "Error Saving Workflow",
          description: "Failed to save workflow to the server",
          variant: "destructive",
        });
        setIsSaving(false);
      }
    },
    [yamlFlow, toast, onSaveComplete],
  );

  // =====================================================================
  // Keyboard shortcuts
  // =====================================================================

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setConnectionSource(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // =====================================================================
  // Return
  // =====================================================================

  return {
    canvasNodes,
    canvasEdges,
    setCanvasNodes,
    buildingBlocksData,
    orchestratorsData,
    conditionsData,
    allBlocksData,
    isLoadingBlocks,
    yamlFlow,

    addNode,
    deleteNode,
    addEdgeInternal,
    deleteEdge,

    connectionSource,
    setConnectionSource,
    handleNodeClick,
    cancelConnection,

    edgeDirectionModal,
    handleEdgeDirectionConfirm,
    handleEdgeDirectionCancel,

    conditionalEdgeModal,
    handleConditionalEdgeConfirm,
    handleConditionalEdgeCancel,

    attachConditionToNode,
    removeConditionFromNode,

    onDragStart,
    onDragEnd,
    isDraggingCondition,

    clearGraph,
    openSaveModal,
    saveGraph,

    isGraphValid,
    validationResult,
    fixSuggestions,
    isValidating,
    validateGraph,

    saveModalOpen,
    setSaveModalOpen,
    isSaving,
    themeColors,
  };
};
