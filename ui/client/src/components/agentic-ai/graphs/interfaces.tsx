import { Edge, Node } from 'reactflow';

export interface INodeData {
  label: string;
  description?: string;
  nodeType: string;
  modelName?: string;
  promptTemplate?: string;
  retriever?: string;
  tools?: string[];
  code?: string;
  entryPoint?: string;
  image?: string;
  className?: string;
  args?: string[];
  kwargs?: { [key: string]: string };
  inputType?: string;
  outputType?: string;
  task?: string;
  category?: string;
  template?: string;
  number_of_conversations?: number
}


export interface IGraph {
  nodes: Node<INodeData>[];
  edges: Edge[];
}

export interface IReactFlowNode extends Node {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: INodeData;
}
