import { QueryClient, QueryFunction } from "@tanstack/react-query";
import axios, { AxiosError } from 'axios';

interface APIErrorResponse {
  error?: string; // Mark `error` as optional since it may not always exist
}

export const api = axios.create({
  baseURL: '/api',  
  // baseURL: '/',
  timeout: 20000, // 20 seconds
  withCredentials: true, // Important: This ensures cookies are sent with requests
});

async function throwIfResNotOk(res: Response) {
  if (!res.ok) {
    const text = (await res.text()) || res.statusText;
    throw new Error(`${res.status}: ${text}`);
  }
}

export async function apiRequest(
  method: string,
  url: string,
  data?: unknown | undefined,
): Promise<Response> {
  const res = await fetch(url, {
    method,
    headers: data ? { "Content-Type": "application/json" } : {},
    body: data ? JSON.stringify(data) : undefined,
    credentials: "include",
  });

  await throwIfResNotOk(res);
  return res;
}

type UnauthorizedBehavior = "returnNull" | "throw";
export const getQueryFn: <T>(options: {
  on401: UnauthorizedBehavior;
}) => QueryFunction<T> =
  ({ on401: unauthorizedBehavior }) =>
  async ({ queryKey }) => {
    const res = await fetch(queryKey[0] as string, {
      credentials: "include",
    });

    if (unauthorizedBehavior === "returnNull" && res.status === 401) {
      return null;
    }

    await throwIfResNotOk(res);
    return await res.json();
  };

  
//Generic QueryFunction for React Query using Axios
export const axiosQueryFn: QueryFunction<any> = async ({ queryKey }) => {
  const [url, params] = queryKey as [string, Record<string, any>?];
  const response = await api.get(url, params ? { params } : undefined);
  return response.data;
};

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      queryFn: axiosQueryFn,
      staleTime: 5 * 60_000,          // cache data for 5 minutes
      retry: 1,                       // retry once on failure
      refetchInterval: false,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
});
