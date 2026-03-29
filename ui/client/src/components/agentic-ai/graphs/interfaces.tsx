export interface IGraph {
  id: string;
  nodes: INode[];
  edges: IEdge[];
}

export interface INode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: {
    label: string;
    id: string;
    templateId?: string;
    nodeConfig?: any;
    summary?: string;
    retriever: { id: string; name: string } | null;
  };
}

export interface IEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  animated?: boolean;
}
