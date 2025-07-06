import { PipelineStatus } from '@/constants/pipelineStatus';

export interface Pipeline {
  id: string;
  name: string;
  status: 'processing' | 'waiting' | 'paused' | 'completed' | 'error';
  progress: number;
  source: DataSourceType;
  projectId: string;
}

export interface DataSource {
  id: string;
  name: string;
  type: DataSourceType;
  status: 'connected' | 'disconnected' | 'error';
  lastSync?: string;
}

export type DataSourceType = 'jira' | 'slack' | 'document' | 'github';

export interface ActivityLog {
  id: string;
  type: 'success' | 'error' | 'info';
  title: string;
  description: string;
  time: string;
  projectId: string;
  sourceType: DataSourceType;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'user' | 'viewer';
  avatar?: string;
}

export interface ProjectStats {
  totalDocuments: number;
  processedDocuments: number;
  vectorCount: number;
  sourceDistribution: {
    [key in DataSourceType]?: {
      count: number;
      percentage: number;
    };
  };
}

export interface Document {
  pipeline_id: string;
  name: string;
  path: string;
  status: PipelineStatus;
  created_at: string;
  file_type: string;
  chunks: number;
  page_count: number;
  full_text: string;
  file_size: string;
  upload_by: string;
  last_updated: string;
  scope: "private" | "public";
  stats: {
    total_tokens?: number;
    avg_chunk_size?: number;
    images_extracted?: number;
    tables_extracted?: number;
    embeddings_created?: number;
    api_calls?: number;
    processing_time?: number;
  };
}
