import { useState, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";
import { RowSelectionState } from "@tanstack/react-table";

interface UseBulkDeleteOptions<T> {
  deleteFunction: (ids: string[]) => Promise<any>;
  queryKeys: string[];
  itemName: string; // e.g., "document" or "channel"
  onSuccess?: () => void;
  getError?: (error: any) => string;
}

export function useBulkDelete<T>({
  deleteFunction,
  queryKeys,
  itemName,
  onSuccess,
  getError,
}: UseBulkDeleteOptions<T>) {
  const [bulkDeleteConfirm, setBulkDeleteConfirm] = useState<{ open: boolean; count: number }>({ 
    open: false, 
    count: 0 
  });
  const [bulkDeleteLoading, setBulkDeleteLoading] = useState(false);
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const handleBulkDelete = async (ids: string[]) => {
    try {
      setBulkDeleteLoading(true);
      // Delete all selected items in a single API call
      await deleteFunction(ids);
      
      // Invalidate queries to refresh the list
      queryKeys.forEach(key => {
        queryClient.invalidateQueries({ queryKey: [key] });
      });
      
      toast({
        title: `✅ ${itemName.charAt(0).toUpperCase() + itemName.slice(1)}s Deleted`,
        description: `Successfully deleted ${ids.length} ${itemName}${ids.length > 1 ? 's' : ''}.`,
        variant: "default",
      });
      
      onSuccess?.();
    } catch (error) {
      console.error(`Error deleting ${itemName}s:`, error);
      const errorMessage = getError 
        ? getError(error)
        : (error instanceof Error ? error.message : `Failed to delete some ${itemName}s.`);
      
      const apiError = (error as any)?.response?.data?.error;
      toast({
        title: `❌ Bulk Deletion Failed`,
        description: apiError || errorMessage,
        variant: "destructive",
      });
      throw error;
    } finally {
      setBulkDeleteLoading(false);
    }
  };

  const handleDeleteSelected = (rowSelection: RowSelectionState) => {
    const selectedIds = Object.keys(rowSelection);
    if (selectedIds.length === 0) return;
    setBulkDeleteConfirm({ 
      open: true, 
      count: selectedIds.length
    });
  };

  const confirmBulkDelete = async (rowSelection: RowSelectionState) => {
    try {
      setBulkDeleteLoading(true);
      const idsToDelete = Object.keys(rowSelection);
      await handleBulkDelete(idsToDelete);
      // Only close modal after successful deletion
      setBulkDeleteConfirm({ open: false, count: 0 });
    } catch (error) {
      // Error already handled in handleBulkDelete - keep modal open on error
      console.error("Bulk delete failed:", error);
    } finally {
      setBulkDeleteLoading(false);
    }
  };

  return {
    bulkDeleteConfirm,
    setBulkDeleteConfirm,
    bulkDeleteLoading,
    handleBulkDelete,
    handleDeleteSelected,
    confirmBulkDelete,
  };
}

/**
 * A simplified bulk delete hook that works with Set-based selection
 * and individual delete functions. Useful for pages that don't use
 * React Query or TanStack Table.
 */
interface UseSimpleBulkDeleteOptions {
  /** Function to delete a single item by id. Second param is 'silent' to suppress individual toasts. */
  deleteItem: (id: string, silent?: boolean) => Promise<any>;
  /** Name of the item type for display (e.g., "element", "resource") */
  itemName: string;
  /** Optional callback after successful deletion */
  onSuccess?: () => void;
  /** Optional callback to get error message from error */
  getError?: (error: any) => string;
}

export function useSimpleBulkDelete({
  deleteItem,
  itemName,
  onSuccess,
  getError,
}: UseSimpleBulkDeleteOptions) {
  const [bulkDeleteConfirm, setBulkDeleteConfirm] = useState<{ open: boolean; count: number }>({
    open: false,
    count: 0,
  });
  const [bulkDeleteLoading, setBulkDeleteLoading] = useState(false);
  const [pendingIds, setPendingIds] = useState<string[]>([]);
  const { toast } = useToast();

  /** Open the confirmation modal for bulk delete */
  const openBulkDeleteConfirm = useCallback((ids: Set<string> | string[]) => {
    const idsArray = Array.isArray(ids) ? ids : Array.from(ids);
    if (idsArray.length === 0) return;
    setPendingIds(idsArray);
    setBulkDeleteConfirm({ open: true, count: idsArray.length });
  }, []);

  /** Close the confirmation modal */
  const closeBulkDeleteConfirm = useCallback(() => {
    if (!bulkDeleteLoading) {
      setBulkDeleteConfirm({ open: false, count: 0 });
      setPendingIds([]);
    }
  }, [bulkDeleteLoading]);

  /** Execute the bulk delete */
  const executeBulkDelete = useCallback(async () => {
    if (pendingIds.length === 0) return;

    setBulkDeleteLoading(true);
    try {
      // Delete all items in parallel and track results (silent=true to suppress individual toasts)
      const results = await Promise.allSettled(pendingIds.map(id => deleteItem(id, true)));
      
      const successCount = results.filter(r => r.status === 'fulfilled').length;
      const failures = results.filter((r): r is PromiseRejectedResult => r.status === 'rejected');
      const failureCount = failures.length;

      // Show success toast only if some deletions succeeded
      if (successCount > 0) {
        toast({
          title: `${itemName.charAt(0).toUpperCase() + itemName.slice(1)}${successCount > 1 ? 's' : ''} Deleted`,
          description: `Successfully deleted ${successCount} ${itemName}${successCount > 1 ? 's' : ''}.`,
          variant: "default",
        });
      }

      // Show error toast if some deletions failed
      if (failureCount > 0) {
        // Get the first error message for display
        const firstError = failures[0]?.reason;
        const errorMessage = getError
          ? getError(firstError)
          : (firstError?.response?.data?.error || firstError?.message || `Failed to delete ${failureCount} ${itemName}${failureCount > 1 ? 's' : ''}.`);

        toast({
          title: `${failureCount} Deletion${failureCount > 1 ? 's' : ''} Failed`,
          description: errorMessage,
          variant: "destructive",
        });
      }

      // Always close modal after operation completes
      setBulkDeleteConfirm({ open: false, count: 0 });
      setPendingIds([]);
      
      // Call success callback if at least some succeeded
      if (successCount > 0) {
        onSuccess?.();
      }
    } catch (error) {
      // This should rarely happen since Promise.allSettled doesn't reject
      console.error(`Error deleting ${itemName}s:`, error);
      toast({
        title: "Bulk Deletion Failed",
        description: "An unexpected error occurred.",
        variant: "destructive",
      });
    } finally {
      setBulkDeleteLoading(false);
    }
  }, [pendingIds, deleteItem, itemName, onSuccess, getError, toast]);

  return {
    bulkDeleteConfirm,
    bulkDeleteLoading,
    openBulkDeleteConfirm,
    closeBulkDeleteConfirm,
    executeBulkDelete,
  };
}

/**
 * Hook for managing Set-based selection state
 */
export function useSetSelection<T extends string = string>(initialIds?: Set<T>) {
  const [selectedIds, setSelectedIds] = useState<Set<T>>(initialIds ?? new Set());

  const handleSelectionChange = useCallback((id: T, isSelected: boolean) => {
    setSelectedIds(prev => {
      const newSet = new Set(prev);
      if (isSelected) {
        newSet.add(id);
      } else {
        newSet.delete(id);
      }
      return newSet;
    });
  }, []);

  const selectAll = useCallback((ids: T[]) => {
    setSelectedIds(new Set(ids));
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const toggleAll = useCallback((allIds: T[]) => {
    setSelectedIds(prev => {
      if (prev.size === allIds.length) {
        return new Set();
      }
      return new Set(allIds);
    });
  }, []);

  const isAllSelected = useCallback((allIds: T[]) => {
    return allIds.length > 0 && selectedIds.size === allIds.length;
  }, [selectedIds]);

  return {
    selectedIds,
    setSelectedIds,
    handleSelectionChange,
    selectAll,
    clearSelection,
    toggleAll,
    isAllSelected,
    selectedCount: selectedIds.size,
  };
}

/**
 * Hook for managing object-based row selection state (RowSelectionState from TanStack Table)
 * Use this for pages that use DataTable/TanStack Table
 */
export function useRowSelection() {
  const [rowSelection, setRowSelection] = useState<Record<string, boolean>>({});

  const handleSelectionChange = useCallback((id: string, isSelected: boolean) => {
    setRowSelection(prev => {
      const newSelection = { ...prev };
      if (isSelected) {
        newSelection[id] = true;
      } else {
        delete newSelection[id];
      }
      return newSelection;
    });
  }, []);

  const selectAll = useCallback((ids: string[]) => {
    const newSelection: Record<string, boolean> = {};
    ids.forEach(id => {
      newSelection[id] = true;
    });
    setRowSelection(newSelection);
  }, []);

  const clearSelection = useCallback(() => {
    setRowSelection({});
  }, []);

  const handleSelectAll = useCallback((checked: boolean, allIds: string[]) => {
    if (checked) {
      selectAll(allIds);
    } else {
      clearSelection();
    }
  }, [selectAll, clearSelection]);

  const isAllSelected = useCallback((allIds: string[]) => {
    return allIds.length > 0 && allIds.every(id => rowSelection[id]);
  }, [rowSelection]);

  const selectedCount = Object.keys(rowSelection).length;

  return {
    rowSelection,
    setRowSelection,
    handleSelectionChange,
    selectAll,
    clearSelection,
    handleSelectAll,
    isAllSelected,
    selectedCount,
  };
}