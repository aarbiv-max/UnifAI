import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { render } from "@/test-utils/render";
import ExecutionTab from "../ExecutionTab";

const axiosMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  delete: vi.fn(),
}));

vi.mock("../../../http/axiosAgentConfig", () => ({
  default: axiosMock,
}));

vi.mock("../chat/ChatInterface", () => ({
  default: () => <div>ChatInterface</div>,
}));

vi.mock("../ExecutionStream", () => ({
  default: () => <div>ExecutionStream</div>,
}));

vi.mock("../graphs/ReactFlowGraph", () => ({
  default: () => <div>ReactFlowGraph</div>,
}));

vi.mock("../WorkflowsPanel", () => ({
  default: () => <div>WorkflowsPanel</div>,
}));

vi.mock("@/components/ui/umamitrack", () => ({
  UmamiTrack: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/contexts/AuthContext", () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth: () => ({
    user: { username: "test-user" },
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    checkAuthStatus: vi.fn(),
  }),
}));

vi.mock("../StreamingDataContext", () => ({
  useStreamingData: () => ({
    nodeListRef: { current: new Map() },
    forceUpdate: vi.fn(),
  }),
}));

vi.mock("@/contexts/AgenticAIContext", () => ({
  AgenticAIProvider: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
  useAgenticAI: () => ({
    cacheBlueprintValidationResults: vi.fn(),
  }),
}));

vi.mock("@/hooks/use-blueprint-validation", () => ({
  useBlueprintValidation: () => ({
    isValidating: false,
    validationResults: null,
    isValid: true,
    validateBlueprint: vi.fn(),
  }),
}));

vi.mock("@/hooks/use-session-management", () => ({
  useSessionManagement: () => ({
    currentMessages: [],
    loadSessionMessages: vi.fn(async (session: any) => session),
    clearMessages: vi.fn(),
    setCurrentMessages: vi.fn(),
  }),
}));

vi.mock("@/hooks/use-sharing-status", () => ({
  checkSessionSharingStatus: vi.fn(async () => false),
}));

vi.mock("@/api/blueprints", () => ({
  getBlueprintInfo: vi.fn(async () => ({
    metadata: { usageScope: "public" },
    spec_dict: { name: "Blueprint" },
  })),
}));

describe("ExecutionTab", () => {
  beforeEach(() => {
    axiosMock.get.mockReset();
    axiosMock.post.mockReset();
    axiosMock.delete.mockReset();
    axiosMock.get.mockResolvedValue({ data: [] });
  });

  it("renders error state when sessions fail to load", async () => {
    axiosMock.get.mockRejectedValue(new Error("Network error"));

    render(<ExecutionTab runId={null} />);

    await waitFor(() => {
      expect(
        screen.getByText("Failed to load chat sessions"),
      ).toBeInTheDocument();
    });
  });

  it("renders empty state when no sessions exist", async () => {
    axiosMock.get.mockResolvedValue({ data: [] });

    render(<ExecutionTab runId={null} />);

    await waitFor(() => {
      expect(
        screen.getByText("No chat sessions available"),
      ).toBeInTheDocument();
    });
  });
});

