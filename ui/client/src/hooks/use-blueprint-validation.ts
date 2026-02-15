import { useState, useCallback } from 'react';
import { BlueprintValidationResult, ElementValidationResult } from '@/types/validation';
import { useToast } from '@/hooks/use-toast';
import { useAgenticAI } from '@/contexts/AgenticAIContext';

export interface UseBlueprintValidationOptions {
  /** Callback when validation state changes */
  onValidationChange?: (isValid: boolean, validationResult: BlueprintValidationResult | null, isValidating: boolean) => void;
  /** Whether to show toast notifications on validation failure */
  showToastOnFailure?: boolean;
  /** Whether to skip caching and always call the API (useful for force-refresh scenarios) */
  skipCache?: boolean;
}

export interface UseBlueprintValidationResult {
  /** Whether validation is currently in progress */
  isValidating: boolean;
  /** Validation results by element ID */
  validationResults: Record<string, ElementValidationResult>;
  /** Whether the current blueprint is valid */
  isValid: boolean;
  /** Function to validate a blueprint by ID */
  validateBlueprint: (blueprintId: string) => Promise<void>;
  /** Function to clear validation state */
  clearValidation: () => void;
}

/**
 * Hook to manage blueprint validation state and logic.
 * Uses AgenticAIContext for caching - valid blueprints are cached for 60 minutes.
 * Used by components that need to validate blueprints and display validation results.
 */
export function useBlueprintValidation(
  options: UseBlueprintValidationOptions = {}
): UseBlueprintValidationResult {
  const { 
    onValidationChange, 
    showToastOnFailure = true,
    skipCache = false,
  } = options;
  
  const { toast } = useToast();
  const { validateBlueprintWithCache, isBlueprintValidationCacheHit } = useAgenticAI();
  
  const [isValidating, setIsValidating] = useState<boolean>(false);
  const [validationResults, setValidationResults] = useState<Record<string, ElementValidationResult>>({});
  const [isValid, setIsValid] = useState<boolean>(true);

  const clearValidation = useCallback(() => {
    setValidationResults({});
    setIsValid(true);
    onValidationChange?.(true, null, false);
  }, [onValidationChange]);

  const validate = useCallback(async (blueprintId: string) => {
    // Check if we have a cache hit (valid result within TTL)
    const isCacheHit = !skipCache && isBlueprintValidationCacheHit(blueprintId);
    
    // Only show loading state if we're actually going to fetch from API (no cache hit)
    if (!isCacheHit) {
      setIsValidating(true);
      setValidationResults({});
      setIsValid(true); // Assume valid until proven otherwise
      onValidationChange?.(true, null, true);
    }
    
    try {
      // Return cached result if valid and within 60 minutes (unless skipCache is true)
      // validateBlueprintWithCache handles all caching internally (both blueprint-level and element-level)
      const result = await validateBlueprintWithCache({ blueprintId }, skipCache);
      setValidationResults(result.element_results || {});
      setIsValid(result.is_valid);
      
      // Notify parent of validation result
      onValidationChange?.(result.is_valid, result, false);
      
      // Show toast if validation failed
      if (!result.is_valid && showToastOnFailure) {
        const errorCount = Object.values(result.element_results).filter(r => !r.is_valid).length;
        toast({
          title: "Workflow Validation Failed",
          description: `${errorCount} element${errorCount !== 1 ? 's' : ''} failed validation.`,
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("Error validating blueprint:", error);
      setIsValid(false);
      
      // Notify parent that validation failed
      onValidationChange?.(false, null, false);
      
      if (showToastOnFailure) {
        toast({
          title: "Validation Error",
          description: "Failed to validate the workflow. Please try again.",
          variant: "destructive",
        });
      }
    } finally {
      setIsValidating(false);
    }
  }, [
    skipCache,
    isBlueprintValidationCacheHit,
    validateBlueprintWithCache,
    onValidationChange, 
    showToastOnFailure, 
    toast,
  ]);

  return {
    isValidating,
    validationResults,
    isValid,
    validateBlueprint: validate,
    clearValidation,
  };
}

