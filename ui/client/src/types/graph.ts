export interface CanvasNode {
  id: string;
  label: string;
  position: { x: number; y: number };
  type: string;
  color: string;
  workspaceData?: BuildingBlock["workspaceData"];
  conditions: BuildingBlock[];
}

export interface CanvasEdge {
  id: string;
  source: string;
  target: string;
  isBidirectional?: boolean;
  isConditional?: boolean;
  branch?: string;
}

export interface CurrentGraph {
  id: string;
  name: string;
  nodes: CanvasNode[];
  edges: CanvasEdge[];
  metadata: {
    created: Date;
    lastModified: Date;
    nodeCount: number;
    edgeCount: number;
  };
}

export interface BuildingBlock {
  id: string;
  type: string;
  label: string;
  color: string;
  description: string;
  workspaceData?: {
    rid: string;
    name: string;
    category: string;
    type: string;
    config: any;
    version: number;
    created: string;
    updated: string;
    nested_refs: string[];
  };
}

export interface CustomNodeData {
  label: string;
  icon: React.ReactNode;
  color: string;
  style: string;
  description: string;
  workspaceData?: {
    rid: string;
    name: string;
    category: string;
    type: string;
    config: any;
    version: number;
    created: string;
    updated: string;
    nested_refs: string[];
  };
  onDelete?: (id: string) => void;
  allBlocks?: BuildingBlock[];
  referencedConditions?: BuildingBlock[];
  onAttachCondition?: (nodeId: string, condition: BuildingBlock) => void;
  onRemoveCondition?: (nodeId: string, conditionRid: string) => void;
}
