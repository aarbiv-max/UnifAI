import { useCallback, useMemo, useState } from "react";
import { RowSelectionState } from "@tanstack/react-table";

/**
 * Map of item id → selected. Same shape as TanStack Table’s `RowSelectionState`
 * so it can be passed through to tables unchanged; also used for cards, lists, etc.
 */
export type ItemSelectionState = RowSelectionState;

/**
 * Multi-select by stable string id (tables, grids, sidebars, etc.).
 * Keeps TanStack-compatible `selection` for `rowSelection` / `onRowSelectionChange` props.
 */
export function useItemSelection() {
  const [selection, setSelection] = useState<ItemSelectionState>({});

  const selectedIds = useMemo(
    () => Object.keys(selection).filter((id) => selection[id] === true),
    [selection],
  );

  const selectedCount = selectedIds.length;

  const toggleSelected = useCallback((id: string, selected: boolean) => {
    setSelection((prev) => {
      const next = { ...prev };
      if (selected) next[id] = true;
      else delete next[id];
      return next;
    });
  }, []);

  const clearSelection = useCallback(() => setSelection({}), []);

  /** Drop keys not in `validIds` (e.g. after search filter or server delete). */
  const pruneToIds = useCallback((validIds: Set<string>) => {
    setSelection((prev) => {
      const next: ItemSelectionState = {};
      for (const id of Object.keys(prev)) {
        if (prev[id] === true && validIds.has(id)) next[id] = true;
      }
      return next;
    });
  }, []);

  return {
    selection,
    setSelection,
    selectedIds,
    selectedCount,
    toggleSelected,
    clearSelection,
    pruneToIds,
  };
}
