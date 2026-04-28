import { useCallback } from "react";
import axios from "@/http/axiosAgentConfig";
import type { ChatSession, ChatSessionData } from "@/types/session";
import {
  usePagedRemoteList,
  PAGED_LIST_DEFAULT_PAGE_SIZE,
  PAGED_LIST_DEFAULT_PREFETCH_AHEAD,
} from "@/hooks/use-paged-remote-list";

export const CHAT_SESSIONS_PAGE_SIZE = PAGED_LIST_DEFAULT_PAGE_SIZE;
export const CHAT_SESSIONS_PREFETCH_AHEAD = PAGED_LIST_DEFAULT_PREFETCH_AHEAD;

export type TransformSessionsPage = (
  items: ChatSessionData[],
  pageIndex: number,
) => Promise<ChatSession[]>;

type UseChatSessionsPaginationOptions = {
  userId: string | undefined;
  blueprintId?: string;
  enabled: boolean;
  transformPage: TransformSessionsPage;
};

/**
 * Paginated user chat sessions with prefetch of the next few pages for snappy "Next".
 */
export function useChatSessionsPagination({
  userId,
  blueprintId,
  enabled,
  transformPage,
}: UseChatSessionsPaginationOptions) {
  const fetchPage = useCallback(
    async (pageIndex: number): Promise<{ items: ChatSession[]; total: number }> => {
      if (!userId) {
        return { items: [], total: 0 };
      }
      const params = new URLSearchParams({
        userId,
        offset: String(pageIndex * CHAT_SESSIONS_PAGE_SIZE),
        limit: String(CHAT_SESSIONS_PAGE_SIZE),
      });
      if (blueprintId) {
        params.set("blueprintId", blueprintId);
      }
      const { data } = await axios.get<{ items: ChatSessionData[]; total: number }>(
        `/sessions/session.user.list.page?${params.toString()}`,
      );
      const items = await transformPage(data.items, pageIndex);
      return { items, total: data.total };
    },
    [userId, blueprintId, transformPage],
  );

  const {
    displayedItems,
    mergeItemInCache,
    removeItemById,
    ...list
  } = usePagedRemoteList<ChatSession>({
    enabled: Boolean(enabled && userId),
    resetKey: `${userId ?? ""}:${blueprintId ?? ""}`,
    pageSize: CHAT_SESSIONS_PAGE_SIZE,
    prefetchAhead: CHAT_SESSIONS_PREFETCH_AHEAD,
    fetchPage,
    listLoadErrorMessage: "Failed to load chat sessions",
    getItemId: (s) => s.id,
  });

  return {
    ...list,
    displayedSessions: displayedItems,
    mergeSessionInCache: mergeItemInCache,
    removeSessionFromCache: removeItemById,
  };
}
