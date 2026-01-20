import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
  default: ({ runId }: { runId: string }) => (
    <div data-testid="chat-interface">ChatInterface {runId}</div>
  ),
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

  it("selects the newest session by default", async () => {
    axiosMock.get.mockResolvedValueOnce({
      data: [
        {
          session_id: "session-old",
          blueprint_id: "bp-old",
          started_at: "2024-01-01T00:00:00.000Z",
          blueprint_exists: true,
          metadata: { title: "Old Session" },
        },
        {
          session_id: "session-new",
          blueprint_id: "bp-new",
          started_at: "2024-02-01T00:00:00.000Z",
          blueprint_exists: true,
          metadata: { title: "New Session" },
        },
      ],
    });

    render(<ExecutionTab runId={null} />);

    await waitFor(() => {
      expect(screen.getByTestId("chat-interface")).toHaveTextContent(
        "ChatInterface session-new",
      );
    });
  });

  it("updates active session content when switching sessions", async () => {
    axiosMock.get.mockResolvedValueOnce({
      data: [
        {
          session_id: "session-a",
          blueprint_id: "bp-a",
          started_at: "2024-01-01T00:00:00.000Z",
          blueprint_exists: true,
          metadata: { title: "Session A" },
        },
        {
          session_id: "session-b",
          blueprint_id: "bp-b",
          started_at: "2024-02-01T00:00:00.000Z",
          blueprint_exists: true,
          metadata: { title: "Session B" },
        },
      ],
    });

    const user = userEvent.setup();
    render(<ExecutionTab runId={null} />);

    expect(await screen.findByText("Session B")).toBeInTheDocument();
    await user.click(screen.getByText("Session A"));

    await waitFor(() => {
      expect(screen.getByTestId("chat-interface")).toHaveTextContent(
        "ChatInterface session-a",
      );
    });
  });

  it("marks disabled sessions visually when blueprint is missing", async () => {
    axiosMock.get.mockResolvedValueOnce({
      data: [
        {
          session_id: "session-disabled",
          blueprint_id: "bp-disabled",
          started_at: "2024-02-01T00:00:00.000Z",
          blueprint_exists: false,
          metadata: { title: "Disabled Session" },
        },
      ],
    });

    render(<ExecutionTab runId={null} />);

    const label = await screen.findByText("Disabled Session");
    const row = label.closest(".opacity-50");
    expect(row).not.toBeNull();
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

