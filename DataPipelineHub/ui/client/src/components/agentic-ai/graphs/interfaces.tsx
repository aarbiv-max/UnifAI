// Define types for node data
import {
  Node,
  Edge,
} from 'reactflow';

export interface NodeData {
  label: string;
  description: string | null;
  style: string;
  icon: React.ReactNode;
  tools: string[];
}

// Define types for GraphFlow structure
export interface NodeDefinition {
  type: string;
  name?: string | null;
  _meta: _NodeMetadata;
  llm?: string | null;
  retriever?: string | null;
  system_message?: string | null;
  retries?: number | null;
  tools: string[] | null;
}

export interface PlanItem {
  name: string;
  node?: NodeDefinition;
  after?: string | string[] | null;
  branches: null;
  exit_condition: null;
  uid: string;
  meta: NodeMetadata | null;
}

export interface GraphFlowMetadata {
  name?: string;
  description?: string;
}

export interface _NodeMetadata {
  category: string,
  description: string,
  display_name: string,
  type: string,
}

export interface NodeMetadata {
  description: string,
  display_name: string,
  tags: string[]
}

export interface LLMDefinition {
  _meta: _NodeMetadata;
  name: string;
  type: string;
  model_name: string;
  base_url: string;
  temperature: number;
}

export interface RetrieverDefinition {
  _meta: _NodeMetadata;
  name: string;
  type: string;
}

export interface GraphFlow {
  conditions?: any[];
  description: string;
  display_description: string,
  display_name: string
  llms?: LLMDefinition[];
  plan: PlanItem[];
  retrievers?: RetrieverDefinition[];
  tools?: any[];
}

export interface FlowObject {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  flow: {
    nodes: Node<NodeData>[];
    edges: Edge[];
  };
}