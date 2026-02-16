import { useState, useEffect, useCallback } from 'react';
import { checkServicesHealth, ServicesHealthResponse, ServiceHealth } from '@/api/health';

/**
 * Polling interval for health checks in milliseconds.
 * Checks every 10 seconds as requested.
 */
const HEALTH_CHECK_INTERVAL_MS = 10000;

/**
 * Return type for the useRemoteServicesHealth hook
 */
export interface UseServicesHealthResult {
    /** Health status of the Docling service */
    docling: ServiceHealth | null;
    /** Health status of the Embedding service */
    embedding: ServiceHealth | null;
    /** Whether document upload should be enabled (both services healthy or local) */
    uploadEnabled: boolean;
    /** Whether the initial health check is still loading */
    isLoading: boolean;
    /** Error message if health check failed */
    error: string | null;
    /** Manually trigger a health check refresh */
    refresh: () => Promise<void>;
}

/**
 * Hook to poll for service health status.
 * 
 * Polls every 10 seconds while the component is mounted.
 * Automatically stops polling when the component unmounts.
 * 
 * @example
 * ```tsx
 * function DocumentsPage() {
 *     const { uploadEnabled, docling, embedding } = useRemoteServicesHealth();
 *     
 *     return (
 *         <Button disabled={!uploadEnabled}>
 *             Upload Document
 *         </Button>
 *     );
 * }
 * ```
 * 
 * @returns UseServicesHealthResult with health status and controls
 */
export function useRemoteServicesHealth(): UseServicesHealthResult {
    const [docling, setDocling] = useState<ServiceHealth | null>(null);
    const [embedding, setEmbedding] = useState<ServiceHealth | null>(null);
    const [uploadEnabled, setUploadEnabled] = useState(true);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchHealth = useCallback(async () => {
        try {
            const response = await checkServicesHealth();
            setDocling(response.docling);
            setEmbedding(response.embedding);
            setUploadEnabled(response.upload_enabled);
            setError(null);
        } catch (err) {
            console.error('Failed to check services health:', err);
            setError('Failed to check services health');
            // On error, assume services might be down (fail-safe)
            setUploadEnabled(false);
        } finally {
            setIsLoading(false);
        }
    }, []);

    // Fetch on mount and poll every 10 seconds
    useEffect(() => {
        // Fetch immediately on mount
        fetchHealth();
        
        // Set up interval for periodic polling
        const interval = setInterval(() => {
            fetchHealth();
        }, HEALTH_CHECK_INTERVAL_MS);

        // Cleanup on unmount - stops polling
        return () => clearInterval(interval);
    }, [fetchHealth]);

    return {
        docling,
        embedding,
        uploadEnabled,
        isLoading,
        error,
        refresh: fetchHealth,
    };
}
