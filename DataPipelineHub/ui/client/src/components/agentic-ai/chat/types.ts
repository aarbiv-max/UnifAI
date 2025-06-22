type NodeStreamState = 'PROGRESS' | 'DONE';

export type ToolEntry = {
  id: string;
  name: string;
  output?: string;
};

export type NodeEntry = {
  node_name: string;
  stream: NodeStreamState;
  text: string;
  tools?: ToolEntry[];
};

export interface Message {
    id: string;
    content: string;
    sender: 'user' | 'ai';
    streamLogs?: StreamLogEntry[];
    finalAnswer?: string;
  }
  
  export interface StreamLogEntry {
    nodeId: string;
    nodeName: string;
    message: string;
    tools: ToolEntry[];
    status: 'processing' | 'complete' | 'error';
    isExpanded?: boolean;
  }