import { api } from '@/lib/queryClient';
import type { Document } from '@/types';

export async function fetchDocuments(): Promise<Document[]> {
  // Call the new backend endpoint for available data sources with source_type='document'
  // Using GET request with query parameters as required by the backend @from_query decorator
  const response = await api.get<{sources: any}>(
    "data_sources/data.sources.get",
    {
      params: {
        source_type: "document"
      }
    }
  );
  return response.data.sources;
};

export async function uploadDocs(files: {name: string, content: string}[]): Promise<any> {
    const uploaded = await api.post<any>(
        'docs/upload',
        { files: files }
      );
}

export async function embedDocs(docs: {source_name: string}[]): Promise<any> {
    const embedded = await api.put<any>(
        'pipelines/embed',
        { 
            data: docs,
            type: 'document'
        }
      );
}

export async function deleteDoc(pipelineId: string): Promise<any> {
    // Call the new backend endpoint for deleting data sources
    const deleted = await api.delete(`data_sources/data.source.delete`, {
        data: { pipeline_id: pipelineId }
    });
    return deleted.data;
};