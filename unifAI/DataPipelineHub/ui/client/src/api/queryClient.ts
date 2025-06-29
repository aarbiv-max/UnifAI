import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60_000,      // cache for 5m
      retry: 2,                   // retry twice on failure
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 1,
    },
  },
});
