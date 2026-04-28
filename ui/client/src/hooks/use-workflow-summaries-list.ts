import { useState, useCallback } from "react";
import { fetchBlueprintSummariesPage } from "@/api/blueprints";
import { convertGraphFlowToFlowObject } from "@/utils/blueprintHelpers";
import type { FlowObject } from "@/components/agentic-ai/graphs/interfaces";
import {
  usePagedRemoteList,
  PAGED_LIST_DEFAULT_PREFETCH_AHEAD,
} from "@/hooks/use-paged-remote-list";
import { useDebouncedValue } from "@/hooks/use-debounced-value";

export const WORKFLOW_LIST_PAGE_SIZE = 12;
const SEARCH_DEBOUNCE_MS = 300;

/**
 * Paginated workflow sidebar: summaries API + optional debounced search.
 */
export function useWorkflowSummariesList(userId: string) {
  const [searchQuery, setSearchQuery] = useState("");
  const debouncedSearch = useDebouncedValue(searchQuery.trim(), SEARCH_DEBOUNCE_MS);

  const fetchPage = useCallback(
    async (pageIndex: number) => {
      const offset = pageIndex * WORKFLOW_LIST_PAGE_SIZE;
      const { items, total } = await fetchBlueprintSummariesPage(
        userId,
        offset,
        WORKFLOW_LIST_PAGE_SIZE,
        debouncedSearch || undefined,
      );
      const flows = items
        .map((summary, i) =>
          convertGraphFlowToFlowObject(
            { name: summary.name, description: summary.description },
            offset + i,
            summary.blueprint_id,
          ),
        )
        .filter((flow): flow is FlowObject => flow !== null);
      return { items: flows, total };
    },
    [userId, debouncedSearch],
  );

  const list = usePagedRemoteList<FlowObject>({
    enabled: true,
    resetKey: `${userId}:${debouncedSearch}`,
    pageSize: WORKFLOW_LIST_PAGE_SIZE,
    prefetchAhead: PAGED_LIST_DEFAULT_PREFETCH_AHEAD,
    fetchPage,
    listLoadErrorMessage: "Failed to load workflows",
    getItemId: (f) => f.id,
  });

  return {
    searchQuery,
    setSearchQuery,
    debouncedSearch,
    ...list,
  };
}
