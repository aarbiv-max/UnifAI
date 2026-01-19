import React, { PropsWithChildren } from "react";
import { render, RenderOptions } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { AuthProvider } from "@/contexts/AuthContext";
import { SharedProvider } from "@/contexts/SharedContext";
import { ProjectProvider } from "@/contexts/ProjectContext";
import { NotificationProvider } from "@/contexts/NotificationContext";
import { AgenticAIProvider } from "@/contexts/AgenticAIContext";

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: false,
      },
    },
  });

type ExtendedRenderOptions = Omit<RenderOptions, "wrapper"> & {
  queryClient?: QueryClient;
};

const Providers = ({
  children,
  queryClient,
}: PropsWithChildren<{ queryClient: QueryClient }>) => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <ThemeProvider>
        <AuthProvider>
          <SharedProvider>
            <ProjectProvider>
              <NotificationProvider>
                <AgenticAIProvider>{children}</AgenticAIProvider>
              </NotificationProvider>
            </ProjectProvider>
          </SharedProvider>
        </AuthProvider>
      </ThemeProvider>
    </TooltipProvider>
  </QueryClientProvider>
);

const renderWithProviders = (
  ui: React.ReactElement,
  options: ExtendedRenderOptions = {},
) => {
  const queryClient = options.queryClient ?? createTestQueryClient();

  return render(ui, {
    ...options,
    wrapper: ({ children }) => (
      <Providers queryClient={queryClient}>{children}</Providers>
    ),
  });
};

export * from "@testing-library/react";
export { renderWithProviders as render, createTestQueryClient };

