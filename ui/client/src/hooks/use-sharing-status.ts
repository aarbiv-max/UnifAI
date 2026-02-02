/**
 * Custom hook for managing blueprint sharing status
 */

import { useState, useCallback } from 'react';
import { getBlueprintInfo } from '@/api/blueprints';

interface UseSharingStatusReturn {
  isSharingDisabled: boolean;
  isLoading: boolean;
  checkSharingStatus: (blueprintId: string) => Promise<void>;
  resetStatus: () => void;
}

/**
 * Hook to manage sharing status for a blueprint
 * Handles fetching and caching the usageScope status from blueprint metadata
 */
export const useSharingStatus = (): UseSharingStatusReturn => {
  const [isSharingDisabled, setIsSharingDisabled] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const checkSharingStatus = useCallback(async (blueprintId: string) => {
    if (!blueprintId) {
      setIsSharingDisabled(false);
      return;
    }

    setIsLoading(true);
    try {
      const blueprintInfo = await getBlueprintInfo(blueprintId);
      const isPublic = blueprintInfo.metadata?.usageScope === "public";
      setIsSharingDisabled(!isPublic);
    } catch (error) {
      // If status check fails, assume sharing is disabled for safety
      console.error('Error checking sharing status:', error);
      setIsSharingDisabled(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const resetStatus = useCallback(() => {
    setIsSharingDisabled(false);
    setIsLoading(false);
  }, []);

  return {
    isSharingDisabled,
    isLoading,
    checkSharingStatus,
    resetStatus,
  };
};

/**
 * Check sharing status for a session by fetching usageScope from blueprint
 * Returns true if sharing is disabled, false if sharing is enabled
 */
export const checkSessionSharingStatus = async (
  blueprintId: string | undefined,
  fromSharedLink: boolean,
  blueprintExists: boolean
): Promise<boolean> => {
  if (!fromSharedLink || !blueprintExists || !blueprintId) {
    return false;
  }

  try {
    const blueprintInfo = await getBlueprintInfo(blueprintId);
    const isPublic = blueprintInfo.metadata?.usageScope === "public";
    return !isPublic;
  } catch (error) {
    // If status check fails, assume sharing is disabled for safety
    console.error('Error checking session sharing status:', error);
    return true;
  }
};

