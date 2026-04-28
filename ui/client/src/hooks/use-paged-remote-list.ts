import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import type { MutableRefObject } from "react";

/** Default page size for sidebar lists (e.g. chats). */
export const PAGED_LIST_DEFAULT_PAGE_SIZE = 10;
export const PAGED_LIST_DEFAULT_PREFETCH_AHEAD = 3;

const EMPTY: unknown[] = [];

function lastPageIndex(total: number, pageSize: number): number {
  if (total <= 0) return 0;
  return Math.max(0, Math.ceil(total / pageSize) - 1);
}

export type FetchPageResult<T> = { items: T[]; total: number };

export type UsePagedRemoteListOptions<T> = {
  enabled: boolean;
  /** When this string changes, cache resets and page 0 reloads (e.g. user id + search). */
  resetKey: string;
  pageSize: number;
  prefetchAhead: number;
  fetchPage: (pageIndex: number) => Promise<FetchPageResult<T>>;
  listLoadErrorMessage?: string;
  /** Enables mergeItemInCache / removeItemById. */
  getItemId?: (item: T) => string;
};

function clearPageCache<T>(refs: {
  loadGenerationRef: MutableRefObject<number>;
  inflightRef: MutableRefObject<Set<number>>;
  pageCacheRef: MutableRefObject<Map<number, T[]>>;
}) {
  refs.loadGenerationRef.current += 1;
  refs.inflightRef.current.clear();
  refs.pageCacheRef.current.clear();
}

/**
 * Offset/limit remote list with per-page cache and prefetch of following pages.
 */
export function usePagedRemoteList<T>({
  enabled,
  resetKey,
  pageSize,
  prefetchAhead,
  fetchPage,
  listLoadErrorMessage = "Failed to load list",
  getItemId,
}: UsePagedRemoteListOptions<T>) {
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(0);
  const [isLoading, setIsLoading] = useState(() => Boolean(enabled));
  const [listLoadError, setListLoadError] = useState<string | null>(null);
  const [isCurrentPageLoading, setIsCurrentPageLoading] = useState(false);
  const [cacheVersion, setCacheVersion] = useState(0);
  const pageCacheRef = useRef(new Map<number, T[]>());
  const loadGenerationRef = useRef(0);
  const inflightRef = useRef(new Set<number>());

  const bump = useCallback(() => setCacheVersion((v) => v + 1), []);

  const loadAndStorePage = useCallback(
    async (pageIndex: number, gen: number): Promise<void> => {
      if (loadGenerationRef.current !== gen) return;
      if (pageCacheRef.current.has(pageIndex)) return;
      if (inflightRef.current.has(pageIndex)) return;
      inflightRef.current.add(pageIndex);
      try {
        const { items, total: t } = await fetchPage(pageIndex);
        if (loadGenerationRef.current !== gen) return;
        pageCacheRef.current.set(pageIndex, items);
        setTotal(t);
        bump();
      } finally {
        inflightRef.current.delete(pageIndex);
      }
    },
    [fetchPage, bump],
  );

  /** Prefetch up to `prefetchAhead` pages after `fromPage` (e.g. after page 0 loads, warm 1..k). */
  const prefetchAheadOf = useCallback(
    (fromPage: number, gen: number, totalCount: number) => {
      for (let p = fromPage + 1; p <= fromPage + prefetchAhead; p += 1) {
        if (p * pageSize >= totalCount) break;
        void loadAndStorePage(p, gen);
      }
    },
    [prefetchAhead, pageSize, loadAndStorePage],
  );

  const applyPage0 = useCallback(
    (gen: number, items: T[], totalCount: number) => {
      if (loadGenerationRef.current !== gen) return;
      pageCacheRef.current.set(0, items);
      setTotal(totalCount);
      setListLoadError(null);
      prefetchAheadOf(0, gen, totalCount);
    },
    [prefetchAheadOf],
  );

  useEffect(() => {
    const refs = { loadGenerationRef, inflightRef, pageCacheRef };

    if (!enabled) {
      clearPageCache(refs);
      setTotal(0);
      setCurrentPage(0);
      setIsLoading(false);
      setIsCurrentPageLoading(false);
      setListLoadError(null);
      bump();
      return;
    }

    clearPageCache(refs);
    const gen = loadGenerationRef.current;
    setTotal(0);
    setCurrentPage(0);
    setListLoadError(null);
    setIsLoading(true);

    fetchPage(0)
      .then(({ items, total: t }) => {
        applyPage0(gen, items, t);
        if (loadGenerationRef.current !== gen) return;
        setIsLoading(false);
        bump();
      })
      .catch(() => {
        if (loadGenerationRef.current !== gen) return;
        setListLoadError(listLoadErrorMessage);
        setIsLoading(false);
        bump();
      });
  }, [enabled, resetKey, fetchPage, applyPage0, bump, listLoadErrorMessage]);

  useEffect(() => {
    if (!enabled || isLoading) return;
    const gen = loadGenerationRef.current;
    const maxPage = lastPageIndex(total, pageSize);
    if (total > 0 && currentPage > maxPage) {
      setCurrentPage(maxPage);
      return;
    }

    if (total > 0 && currentPage * pageSize >= total) {
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

    prefetchAheadOf(currentPage, gen, total);
  }, [currentPage, enabled, isLoading, total, loadAndStorePage, prefetchAheadOf, pageSize]);

  const displayedItems = useMemo(() => {
    void cacheVersion;
    return pageCacheRef.current.get(currentPage) ?? (EMPTY as T[]);
  }, [currentPage, cacheVersion]);

  const maxPageIndex = lastPageIndex(total, pageSize);

  const peekPage = useCallback((pageIndex: number): T[] => {
    return pageCacheRef.current.get(pageIndex) ?? (EMPTY as T[]);
  }, []);

  const goToPrevPage = useCallback(() => {
    setCurrentPage((p) => Math.max(0, p - 1));
  }, []);

  const goToNextPage = useCallback(() => {
    setCurrentPage((p) => Math.min(lastPageIndex(total, pageSize), p + 1));
  }, [total, pageSize]);

  const refresh = useCallback((): Promise<void> => {
    if (!enabled) {
      return Promise.resolve();
    }
    clearPageCache({ loadGenerationRef, inflightRef, pageCacheRef });
    const gen = loadGenerationRef.current;
    setTotal(0);
    setCurrentPage(0);
    setListLoadError(null);
    setIsLoading(true);
    return fetchPage(0)
      .then(({ items, total: t }) => {
        applyPage0(gen, items, t);
      })
      .catch(() => {
        if (loadGenerationRef.current !== gen) return;
        setListLoadError(listLoadErrorMessage);
      })
      .finally(() => {
        if (loadGenerationRef.current !== gen) return;
        setIsLoading(false);
        bump();
      });
  }, [enabled, fetchPage, applyPage0, bump, listLoadErrorMessage]);

  const mergeItemInCache = useCallback(
    (updated: T) => {
      if (!getItemId) return;
      const id = getItemId(updated);
      const next = new Map(pageCacheRef.current);
      let changed = false;
      for (const [key, list] of next) {
        if (!list.some((s) => getItemId(s) === id)) continue;
        next.set(
          key,
          list.map((s) =>
            getItemId(s) === id ? (Object.assign({}, s as object, updated as object) as T) : s,
          ),
        );
        changed = true;
      }
      if (changed) {
        pageCacheRef.current = next;
        bump();
      }
    },
    [bump, getItemId],
  );

  const removeItemById = useCallback(
    (itemId: string) => {
      if (!getItemId) return;
      const next = new Map<number, T[]>();
      let removed = false;
      for (const [key, list] of pageCacheRef.current) {
        const filtered = list.filter((s) => getItemId(s) !== itemId);
        if (filtered.length !== list.length) removed = true;
        if (filtered.length > 0) next.set(key, filtered);
      }
      pageCacheRef.current = next;
      if (removed) {
        setTotal((t) => Math.max(0, t - 1));
        bump();
      }
    },
    [bump, getItemId],
  );

  return {
    total,
    currentPage,
    setCurrentPage,
    displayedItems,
    isLoading,
    listLoadError,
    isCurrentPageLoading,
    goToPrevPage,
    goToNextPage,
    refresh,
    maxPageIndex,
    peekPage,
    mergeItemInCache,
    removeItemById,
  };
}
