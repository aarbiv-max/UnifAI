import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import axios from "@/http/axiosAgentConfig";
import type { ChatSession, ChatSessionData } from "@/types/session";

export const CHAT_SESSIONS_PAGE_SIZE = 10;
export const CHAT_SESSIONS_PREFETCH_AHEAD = 3;

export type TransformSessionsPage = (
  items: ChatSessionData[],
  pageIndex: number,
) => Promise<ChatSession[]>;

const EMPTY_LIST: ChatSession[] = [];

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
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(0);
  const [isLoading, setIsLoading] = useState(() => Boolean(enabled && userId));
  const [listLoadError, setListLoadError] = useState<string | null>(null);
  const [isCurrentPageLoading, setIsCurrentPageLoading] = useState(false);
  const [cacheVersion, setCacheVersion] = useState(0);
  const pageCacheRef = useRef(new Map<number, ChatSession[]>());
  const loadGenerationRef = useRef(0);
  const inflightRef = useRef(new Set<number>());

  const bump = useCallback(() => setCacheVersion((v) => v + 1), []);

  const fetchPageFromApi = useCallback(
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
      const transformed = await transformPage(data.items, pageIndex);
      return { items: transformed, total: data.total };
    },
    [userId, blueprintId, transformPage],
  );

  const loadAndStorePage = useCallback(
    async (pageIndex: number, gen: number): Promise<void> => {
      if (loadGenerationRef.current !== gen) return;
      if (pageCacheRef.current.has(pageIndex)) return;
      if (inflightRef.current.has(pageIndex)) return;
      inflightRef.current.add(pageIndex);
      try {
        const { items, total: t } = await fetchPageFromApi(pageIndex);
        if (loadGenerationRef.current !== gen) return;
        pageCacheRef.current.set(pageIndex, items);
        setTotal(t);
        bump();
      } finally {
        inflightRef.current.delete(pageIndex);
      }
    },
    [fetchPageFromApi, bump],
  );

  useEffect(() => {
    if (!enabled || !userId) {
      loadGenerationRef.current += 1;
      inflightRef.current.clear();
      pageCacheRef.current.clear();
      setTotal(0);
      setCurrentPage(0);
      setIsLoading(false);
      setIsCurrentPageLoading(false);
      setListLoadError(null);
      bump();
      return;
    }

    loadGenerationRef.current += 1;
    const gen = loadGenerationRef.current;
    inflightRef.current.clear();
    pageCacheRef.current.clear();
    setTotal(0);
    setCurrentPage(0);
    setListLoadError(null);
    setIsLoading(true);

    fetchPageFromApi(0)
      .then(({ items, total: t }) => {
        if (loadGenerationRef.current !== gen) return;
        pageCacheRef.current.set(0, items);
        setTotal(t);
        setListLoadError(null);
        setIsLoading(false);
        bump();
        for (let p = 1; p <= CHAT_SESSIONS_PREFETCH_AHEAD; p += 1) {
          if (p * CHAT_SESSIONS_PAGE_SIZE >= t) break;
          void loadAndStorePage(p, gen);
        }
      })
      .catch(() => {
        if (loadGenerationRef.current !== gen) return;
        setListLoadError("Failed to load chat sessions");
        setIsLoading(false);
        bump();
      });
  }, [enabled, userId, blueprintId, fetchPageFromApi, loadAndStorePage, bump]);

  useEffect(() => {
    if (!enabled || !userId || isLoading) return;
    const gen = loadGenerationRef.current;
    const maxPage = Math.max(0, Math.ceil(total / CHAT_SESSIONS_PAGE_SIZE) - 1);
    if (total > 0 && currentPage > maxPage) {
      setCurrentPage(maxPage);
      return;
    }

    const offset = currentPage * CHAT_SESSIONS_PAGE_SIZE;
    if (total > 0 && offset >= total) {
      return;
    }

    if (!pageCacheRef.current.has(currentPage)) {
      setIsCurrentPageLoading(true);
      void loadAndStorePage(currentPage, gen).finally(() => {
        if (loadGenerationRef.current !== gen) return;
        setIsCurrentPageLoading(false);
      });
    } else {
      setIsCurrentPageLoading(false);
    }

    for (let p = currentPage + 1; p <= currentPage + CHAT_SESSIONS_PREFETCH_AHEAD; p += 1) {
      if (p * CHAT_SESSIONS_PAGE_SIZE >= total) break;
      void loadAndStorePage(p, gen);
    }
  }, [currentPage, enabled, userId, isLoading, total, loadAndStorePage]);

  const displayedSessions = useMemo(() => {
    void cacheVersion;
    return pageCacheRef.current.get(currentPage) ?? EMPTY_LIST;
  }, [currentPage, cacheVersion]);

  const maxPageIndex = Math.max(0, Math.ceil(total / CHAT_SESSIONS_PAGE_SIZE) - 1);

  const peekPage = useCallback((pageIndex: number): ChatSession[] => {
    return pageCacheRef.current.get(pageIndex) ?? EMPTY_LIST;
  }, []);

  const goToPrevPage = useCallback(() => {
    setCurrentPage((p) => Math.max(0, p - 1));
  }, []);

  const goToNextPage = useCallback(() => {
    setCurrentPage((p) => {
      const max = Math.max(0, Math.ceil(total / CHAT_SESSIONS_PAGE_SIZE) - 1);
      return Math.min(max, p + 1);
    });
  }, [total]);

  const refresh = useCallback((): Promise<void> => {
    if (!userId) {
      return Promise.resolve();
    }
    loadGenerationRef.current += 1;
    const gen = loadGenerationRef.current;
    inflightRef.current.clear();
    pageCacheRef.current.clear();
    setTotal(0);
    setCurrentPage(0);
    setListLoadError(null);
    setIsLoading(true);
    return fetchPageFromApi(0)
      .then(({ items, total: t }) => {
        if (loadGenerationRef.current !== gen) return;
        pageCacheRef.current.set(0, items);
        setTotal(t);
        setListLoadError(null);
        for (let p = 1; p <= CHAT_SESSIONS_PREFETCH_AHEAD; p += 1) {
          if (p * CHAT_SESSIONS_PAGE_SIZE >= t) break;
          void loadAndStorePage(p, gen);
        }
      })
      .catch(() => {
        if (loadGenerationRef.current !== gen) return;
        setListLoadError("Failed to load chat sessions");
      })
      .finally(() => {
        if (loadGenerationRef.current !== gen) return;
        setIsLoading(false);
        bump();
      });
  }, [userId, fetchPageFromApi, loadAndStorePage, bump]);

  const mergeSessionInCache = useCallback(
    (updated: ChatSession) => {
      const next = new Map(pageCacheRef.current);
      let changed = false;
      for (const [key, list] of next) {
        if (!list.some((s) => s.id === updated.id)) continue;
        next.set(
          key,
          list.map((s) => (s.id === updated.id ? { ...s, ...updated } : s)),
        );
        changed = true;
      }
      if (changed) {
        pageCacheRef.current = next;
        bump();
      }
    },
    [bump],
  );

  const removeSessionFromCache = useCallback(
    (sessionId: string) => {
      const next = new Map<number, ChatSession[]>();
      let removed = false;
      for (const [key, list] of pageCacheRef.current) {
        const filtered = list.filter((s) => s.id !== sessionId);
        if (filtered.length !== list.length) removed = true;
        if (filtered.length > 0) next.set(key, filtered);
      }
      pageCacheRef.current = next;
      if (removed) {
        setTotal((t) => Math.max(0, t - 1));
        bump();
      }
    },
    [bump],
  );

  return {
    total,
    currentPage,
    setCurrentPage,
    displayedSessions,
    isLoading,
    listLoadError,
    isCurrentPageLoading,
    goToPrevPage,
    goToNextPage,
    refresh,
    mergeSessionInCache,
    removeSessionFromCache,
    maxPageIndex,
    peekPage,
  };
}
