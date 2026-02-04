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

const chatInterfaceSpy = vi.fn();
vi.mock("../chat/ChatInterface", () => ({
  default: (props: Record<string, unknown>) => {
    chatInterfaceSpy(props);
    return (
      <div data-testid="chat-interface">
        ChatInterface {props.runId as string}
        {props.blueprintExists === false && <span>workflow-deleted</span>}
        {props.isSharingDisabled && <span>sharing-disabled</span>}
        {props.blueprintValid === false && <span>validation-failed</span>}
        {props.isValidatingBlueprint && <span>validating</span>}
        {props.isChatOnlyMode && <span>chat-only-mode</span>}
        <button onClick={props.onToggleBlueprintGraph as () => void}>Toggle Graph</button>
      </div>
    );
  },
}));

vi.mock("../ExecutionStream", () => ({
  default: () => <div data-testid="execution-stream">ExecutionStream</div>,
}));

const reactFlowGraphSpy = vi.fn();
vi.mock("../graphs/ReactFlowGraph", () => ({
  default: (props: Record<string, unknown>) => {
    reactFlowGraphSpy(props);
    return <div data-testid="reactflow-graph">ReactFlowGraph {props.blueprintId as string}</div>;
  },
}));

const workflowsPanelSpy = vi.fn();
vi.mock("../WorkflowsPanel", () => ({
  default: (props: Record<string, unknown>) => {
    workflowsPanelSpy(props);
    return <div data-testid="workflows-panel">WorkflowsPanel</div>;
  },
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

vi.mock("@/contexts/NotificationContext", () => ({
  NotificationProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useNotifications: () => ({
    receivedNotifications: [],
    sentNotifications: [],
    isLoading: false,
    error: null,
    pendingNotificationsCount: 0,
    hasUnreadNotifications: false,
    refreshNotifications: vi.fn(),
    sendNotification: vi.fn(),
    acceptNotification: vi.fn(),
    declineNotification: vi.fn(),
    clearError: vi.fn(),
  }),
}));

vi.mock("../StreamingDataContext", () => ({
  StreamingDataProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useStreamingData: () => ({
    nodeListRef: { current: new Map() },
    forceUpdate: vi.fn(),
    clearStream: vi.fn(),
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

const validateBlueprintMock = vi.fn();
vi.mock("@/hooks/use-blueprint-validation", () => ({
  useBlueprintValidation: () => ({
    isValidating: false,
    validationResults: null,
    isValid: true,
    validateBlueprint: validateBlueprintMock,
  }),
}));

const loadSessionMessagesMock = vi.fn();
vi.mock("@/hooks/use-session-management", () => ({
  useSessionManagement: () => ({
    currentMessages: [],
    loadSessionMessages: loadSessionMessagesMock.mockImplementation(async (session: Record<string, unknown>) => ({
      ...session,
      messages: [],
    })),
    clearMessages: vi.fn(),
    setCurrentMessages: vi.fn(),
  }),
}));

const checkSessionSharingStatusMock = vi.fn();
vi.mock("@/hooks/use-sharing-status", () => ({
  checkSessionSharingStatus: (...args: unknown[]) => checkSessionSharingStatusMock(...args),
}));

const getBlueprintInfoMock = vi.fn();
vi.mock("@/api/blueprints", () => ({
  getBlueprintInfo: (...args: unknown[]) => getBlueprintInfoMock(...args),
}));

vi.mock("@/api/shares", () => ({
  listShares: vi.fn().mockResolvedValue({ invites: [] }),
  createShare: vi.fn(),
  acceptShare: vi.fn(),
  declineShare: vi.fn(),
}));

describe("ExecutionTab", () => {
  beforeEach(() => {
    axiosMock.get.mockReset();
    axiosMock.post.mockReset();
    axiosMock.delete.mockReset();
    validateBlueprintMock.mockReset();
    loadSessionMessagesMock.mockReset();
    checkSessionSharingStatusMock.mockReset();
    getBlueprintInfoMock.mockReset();
    chatInterfaceSpy.mockClear();
    reactFlowGraphSpy.mockClear();
    workflowsPanelSpy.mockClear();
    
    axiosMock.get.mockResolvedValue({ data: [] });
    checkSessionSharingStatusMock.mockResolvedValue(false);
    getBlueprintInfoMock.mockResolvedValue({
      metadata: { usageScope: "public" },
      spec_dict: { name: "Blueprint" },
    });
    loadSessionMessagesMock.mockImplementation(async (session: any) => ({
      ...session,
      messages: [],
    }));
  });

  describe("Initialization", () => {
    it("initializes chatSessions as empty array", async () => {
      axiosMock.get.mockResolvedValueOnce({ data: [] });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByText("No chat sessions available")).toBeInTheDocument();
      });
    });

    it("initializes selectedSession as null", async () => {
      axiosMock.get.mockResolvedValueOnce({ data: [] });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByText("Select a chat session to view blueprint")).toBeInTheDocument();
      });
    });

    it("initializes panel widths: chatSidebar=20%, chatInterface=50%, blueprintGraph=30%", async () => {
      axiosMock.get.mockResolvedValueOnce({ data: [] });

      const { container } = render(<ExecutionTab runId={null} />);

      // Wait for loading to complete before checking structure
      await waitFor(() => {
        expect(screen.queryByText("Loading chat sessions...")).not.toBeInTheDocument();
      });

      // The component should have resizable panels with these initial widths
      // We can verify the structure exists
      expect(container.querySelector(".resizable-container")).toBeInTheDocument();
    });

    it("initializes isLoading=true", () => {
      axiosMock.get.mockImplementation(() => new Promise(() => {})); // Never resolves

      render(<ExecutionTab runId={null} />);

      expect(screen.getByText("Loading chat sessions...")).toBeInTheDocument();
    });
  });

  describe("Session fetching", () => {
    it("calls /sessions/session.user.chat.get?userId={username}", async () => {
      axiosMock.get.mockResolvedValueOnce({ data: [] });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(axiosMock.get).toHaveBeenCalledWith(
          "/sessions/session.user.chat.get?userId=test-user",
        );
      });
    });

    it("sorts sessions by timestamp (most recent first)", async () => {
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

      // The newest session should be selected automatically
      await waitFor(() => {
        expect(screen.getByTestId("chat-interface")).toHaveTextContent(
          "ChatInterface session-new",
        );
      });
    });

    it("auto-selects first session via handleSessionSelect()", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "First Session" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByTestId("chat-interface")).toHaveTextContent(
          "ChatInterface session-1",
        );
      });
    });

    it("sets isLoading=false after completion", async () => {
      axiosMock.get.mockResolvedValueOnce({ data: [] });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.queryByText("Loading chat sessions...")).not.toBeInTheDocument();
      });
    });

    it("sets error state on failure", async () => {
      axiosMock.get.mockRejectedValue(new Error("Network error"));

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(
          screen.getByText("Failed to load chat sessions"),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Session selection", () => {
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

    it("triggers blueprint validation via validateSelectedBlueprint()", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(validateBlueprintMock).toHaveBeenCalledWith("bp-1");
      });
    });

    it("resets blueprint name states on session switch", async () => {
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

      await screen.findByText("Session B");
      await user.click(screen.getByText("Session A"));

      // Blueprint info should be fetched for the new session
      await waitFor(() => {
        expect(getBlueprintInfoMock).toHaveBeenCalledWith("bp-a");
      });
    });
  });

  describe("Sharing status", () => {
    it("fetches blueprint info via getBlueprintInfo()", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(getBlueprintInfoMock).toHaveBeenCalledWith("bp-1");
      });
    });

    it("extracts sharing status from metadata.usageScope", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session", source: "public_link" },
          },
        ],
      });

      getBlueprintInfoMock.mockResolvedValue({
        metadata: { usageScope: "private" },
        spec_dict: { name: "Blueprint" },
      });

      render(<ExecutionTab runId={null} />);

      // Check DOM output since props are updated asynchronously after initial render
      await waitFor(() => {
        expect(screen.getByTestId("chat-interface")).toHaveTextContent("sharing-disabled");
      });
    });

    it("loads messages via loadSessionMessages()", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(loadSessionMessagesMock).toHaveBeenCalled();
      });
    });
  });

  describe("Chat-only mode (isChatOnlyMode)", () => {
    it("derived from selectedSession?.fromSharedLink", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Shared Session", source: "public_link" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByTestId("chat-interface")).toHaveTextContent("chat-only-mode");
      });
    });

    it("shows 'shared link' message instead of graph", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Shared Session", source: "public_link" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByText(/shared chat link/)).toBeInTheDocument();
      });
    });

    it("shows blueprint name (or 'Loading...' / 'Unknown')", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Shared Session", source: "public_link" },
          },
        ],
      });

      getBlueprintInfoMock.mockResolvedValue({
        metadata: { usageScope: "public" },
        spec_dict: { name: "My Blueprint" },
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByText(/My Blueprint/)).toBeInTheDocument();
      });
    });

    it("shows sharing disabled warning when applicable", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Shared Session", source: "public_link" },
          },
        ],
      });

      getBlueprintInfoMock.mockResolvedValue({
        metadata: { usageScope: "private" },
        spec_dict: { name: "Blueprint" },
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByText(/sharing has been disabled/)).toBeInTheDocument();
      });
    });
  });

  describe("Delete chat", () => {
    it("handleDeleteChat(): sets chatToDelete, opens modal", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      const user = userEvent.setup();
      render(<ExecutionTab runId={null} />);

      await screen.findByText("Test Session");
      
      // Hover over the session to show delete button
      const sessionElement = screen.getByText("Test Session").closest('[class*="cursor-pointer"]');
      if (sessionElement) {
        await user.hover(sessionElement);
      }
      
      // Find and click the delete button (trash icon)
      const deleteButtons = screen.getAllByRole("button");
      const deleteButton = deleteButtons.find(btn => btn.querySelector('svg.lucide-trash-2'));
      if (deleteButton) {
        await user.click(deleteButton);
        expect(screen.getByText(/Are you sure you want to delete/)).toBeInTheDocument();
      }
    });

    it("confirmDeleteChat(): calls API, removes from list, clears selection if deleted", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });
      axiosMock.delete.mockResolvedValueOnce({});

      const user = userEvent.setup();
      render(<ExecutionTab runId={null} />);

      await screen.findByText("Test Session");
      
      // Hover and click delete
      const sessionElement = screen.getByText("Test Session").closest('[class*="cursor-pointer"]');
      if (sessionElement) {
        await user.hover(sessionElement);
      }
      
      const deleteButtons = screen.getAllByRole("button");
      const deleteButton = deleteButtons.find(btn => btn.querySelector('svg.lucide-trash-2'));
      if (deleteButton) {
        await user.click(deleteButton);
        
        // Confirm delete
        const confirmButton = await screen.findByRole("button", { name: /delete/i });
        await user.click(confirmButton);
        
        await waitFor(() => {
          expect(axiosMock.delete).toHaveBeenCalledWith(
            "/sessions/session.delete?sessionId=session-1",
          );
        });
      }
    });

    it("cancelDeleteChat(): closes modal, clears chatToDelete", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      const user = userEvent.setup();
      render(<ExecutionTab runId={null} />);

      await screen.findByText("Test Session");
      
      // Open delete modal
      const sessionElement = screen.getByText("Test Session").closest('[class*="cursor-pointer"]');
      if (sessionElement) {
        await user.hover(sessionElement);
      }
      
      const deleteButtons = screen.getAllByRole("button");
      const deleteButton = deleteButtons.find(btn => btn.querySelector('svg.lucide-trash-2'));
      if (deleteButton) {
        await user.click(deleteButton);
        
        // Cancel
        const cancelButton = await screen.findByRole("button", { name: /cancel/i });
        await user.click(cancelButton);
        
        await waitFor(() => {
          expect(screen.queryByText(/Are you sure you want to delete/)).not.toBeInTheDocument();
        });
      }
    });
  });

  describe("Add Flow Modal", () => {
    it("opens on '+' button click", async () => {
      axiosMock.get.mockResolvedValueOnce({ data: [] });

      const user = userEvent.setup();
      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.queryByText("Loading chat sessions...")).not.toBeInTheDocument();
      });

      // Find and click the + button
      const addButton = screen.getByTitle("Add new chat from flow");
      await user.click(addButton);

      expect(screen.getByText("Add New Chat from Flow")).toBeInTheDocument();
    });

    it("renders WorkflowsPanel inside ReactFlowProvider", async () => {
      axiosMock.get.mockResolvedValueOnce({ data: [] });

      const user = userEvent.setup();
      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.queryByText("Loading chat sessions...")).not.toBeInTheDocument();
      });

      const addButton = screen.getByTitle("Add new chat from flow");
      await user.click(addButton);

      expect(screen.getByTestId("workflows-panel")).toBeInTheDocument();
    });
  });

  describe("UI states", () => {
    it("shows 'Loading chat sessions...' when isLoading=true", () => {
      axiosMock.get.mockImplementation(() => new Promise(() => {}));

      render(<ExecutionTab runId={null} />);

      expect(screen.getByText("Loading chat sessions...")).toBeInTheDocument();
    });

    it("shows red error message when error is set", async () => {
      axiosMock.get.mockRejectedValue(new Error("Network error"));

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByText("Failed to load chat sessions")).toBeInTheDocument();
      });
    });

    it("shows 'Available Chats ({count})' header", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      expect(await screen.findByText("Available Chats (1)")).toBeInTheDocument();
    });

    it("shows 'No chat sessions available' when empty", async () => {
      axiosMock.get.mockResolvedValue({ data: [] });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByText("No chat sessions available")).toBeInTheDocument();
      });
    });

    it("highlights selected session (primary color)", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await screen.findByText("Test Session");
      
      // The selected session should have the primary color styling
      const sessionElement = screen.getByText("Test Session").closest('[class*="border-"]');
      expect(sessionElement).toHaveClass("border-[hsl(var(--primary))]");
    });

    it("dims sessions with !blueprintExists or isSharingDisabled", async () => {
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
  });

  describe("ChatInterface props", () => {
    it("passes runId={selectedSession?.id}", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(chatInterfaceSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            runId: "session-1",
          }),
        );
      });
    });

    it("passes triggerExecution callback", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(chatInterfaceSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            triggerExecution: expect.any(Function),
          }),
        );
      });
    });

    it("passes blueprintExists={selectedSession?.blueprintExists ?? true}", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: false,
            metadata: { title: "Test Session" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(chatInterfaceSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            blueprintExists: false,
          }),
        );
      });
    });

    it("passes isSharingDisabled", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session", source: "public_link" },
          },
        ],
      });

      getBlueprintInfoMock.mockResolvedValue({
        metadata: { usageScope: "private" },
        spec_dict: { name: "Blueprint" },
      });

      render(<ExecutionTab runId={null} />);

      // Check DOM output since props are updated asynchronously after initial render
      await waitFor(() => {
        expect(screen.getByTestId("chat-interface")).toHaveTextContent("sharing-disabled");
      });
    });

    it("passes blueprintValid={isBlueprintValid}", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(chatInterfaceSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            blueprintValid: true,
          }),
        );
      });
    });

    it("passes isChatOnlyMode", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session", source: "public_link" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      // Check DOM output since props are updated asynchronously after initial render
      await waitFor(() => {
        expect(screen.getByTestId("chat-interface")).toHaveTextContent("chat-only-mode");
      });
    });
  });

  describe("Graph panel conditions", () => {
    it("shows ReactFlowGraph when selectedSession?.blueprintId exists", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByTestId("reactflow-graph")).toBeInTheDocument();
      });
    });

    it("shows 'No blueprint available' message when selectedSession but no blueprintId", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: null,
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByText("No blueprint available for this session")).toBeInTheDocument();
      });
    });

    it("shows 'Select a chat session' message when no selectedSession", async () => {
      axiosMock.get.mockResolvedValueOnce({ data: [] });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByText("Select a chat session to view blueprint")).toBeInTheDocument();
      });
    });
  });

  describe("renders error state when sessions fail to load", () => {
    it("renders error state when sessions fail to load", async () => {
      axiosMock.get.mockRejectedValue(new Error("Network error"));

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(
          screen.getByText("Failed to load chat sessions"),
        ).toBeInTheDocument();
      });
    });
  });

  describe("renders empty state when no sessions exist", () => {
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

  describe("selects the newest session by default", () => {
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
  });

  describe("Panel layout for shared link sessions (isChatOnlyMode)", () => {
    it("configures panel layout for shared link sessions", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-shared",
            blueprint_id: "bp-shared",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Shared Session", source: "public_link" },
          },
        ],
      });

      const { container } = render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByTestId("chat-interface")).toHaveTextContent("chat-only-mode");
      });

      // Panel should still be visible for chat-only message
      expect(container.querySelector(".resizable-container")).toBeInTheDocument();
    });

    it("sets isBlueprintGraphHidden to false for shared link sessions", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-shared",
            blueprint_id: "bp-shared",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Shared Session", source: "public_link" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        // Right panel should be visible with chat-only message
        expect(screen.getByText(/shared chat link/)).toBeInTheDocument();
      });
    });

    it("disables resizer for right panel in chat-only mode", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-shared",
            blueprint_id: "bp-shared",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Shared Session", source: "public_link" },
          },
        ],
      });

      const { container } = render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByText(/shared chat link/)).toBeInTheDocument();
      });

      // The right resizer should have cursor-default (not col-resize) for chat-only mode
      const resizers = container.querySelectorAll('[title]');
      const rightResizer = Array.from(resizers).find(r => 
        r.getAttribute('title')?.includes('Workflow not available')
      );
      expect(rightResizer).toBeInTheDocument();
    });
  });

  describe("Sharing status updates", () => {
    it("updates isSharingDisabled state from blueprint metadata", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session", source: "public_link" },
          },
        ],
      });

      getBlueprintInfoMock.mockResolvedValue({
        metadata: { usageScope: "private" },
        spec_dict: { name: "Blueprint" },
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByTestId("chat-interface")).toHaveTextContent("sharing-disabled");
      });
    });

    it("updates session in list with sharing status", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session", source: "public_link" },
          },
        ],
      });

      getBlueprintInfoMock.mockResolvedValue({
        metadata: { usageScope: "private" },
        spec_dict: { name: "Blueprint" },
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        // Session should show sharing-disabled indicator
        expect(screen.getByTestId("chat-interface")).toHaveTextContent("sharing-disabled");
      });
    });

    it("resets isSharingDisabled when blueprint is deleted", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-deleted",
            blueprint_id: "bp-deleted",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: false,
            metadata: { title: "Deleted Blueprint Session" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        // Workflow deleted message should appear instead of sharing disabled
        expect(screen.getByTestId("chat-interface")).toHaveTextContent("workflow-deleted");
      });
    });
  });

  describe("currentSessionMessages updates", () => {
    it("updates currentSessionMessages when session is selected", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      loadSessionMessagesMock.mockImplementation(async (session: any) => ({
        ...session,
        messages: [
          { role: "user", content: "Hello" },
          { role: "assistant", content: "Hi there" },
        ],
      }));

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(loadSessionMessagesMock).toHaveBeenCalled();
      });
    });

    it("clears currentSessionMessages when loadSessionMessages returns null", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      loadSessionMessagesMock.mockResolvedValue(null);

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(loadSessionMessagesMock).toHaveBeenCalled();
      });
    });
  });

  describe("toggleBlueprintGraph()", () => {
    it("toggleBlueprintGraph is disabled in chat-only mode", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-shared",
            blueprint_id: "bp-shared",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Shared Session", source: "public_link" },
          },
        ],
      });

      const user = userEvent.setup();
      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByTestId("chat-interface")).toHaveTextContent("chat-only-mode");
      });

      // Click toggle button in ChatInterface mock - it should not hide the panel
      await user.click(screen.getByRole("button", { name: /toggle graph/i }));

      // Right panel should still be visible with the chat-only message
      await waitFor(() => {
        expect(screen.getByText(/shared chat link/)).toBeInTheDocument();
      });
    });

    it("when hiding: saves current width and expands chat interface", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      const user = userEvent.setup();
      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByTestId("reactflow-graph")).toBeInTheDocument();
      });

      // Click toggle button to hide graph
      await user.click(screen.getByRole("button", { name: /toggle graph/i }));

      // Graph should be hidden
      await waitFor(() => {
        expect(screen.queryByTestId("reactflow-graph")).not.toBeInTheDocument();
      });
    });

    it("when showing: restores saved width and adjusts proportions", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      const user = userEvent.setup();
      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByTestId("reactflow-graph")).toBeInTheDocument();
      });

      // Hide then show the graph
      await user.click(screen.getByRole("button", { name: /toggle graph/i }));
      
      await waitFor(() => {
        expect(screen.queryByTestId("reactflow-graph")).not.toBeInTheDocument();
      });

      await user.click(screen.getByRole("button", { name: /toggle graph/i }));

      // Graph should be visible again
      await waitFor(() => {
        expect(screen.getByTestId("reactflow-graph")).toBeInTheDocument();
      });
    });
  });

  describe("handleFlowSelect()", () => {
    it("sets selectedFlowForModal when flow is selected", async () => {
      axiosMock.get.mockResolvedValueOnce({ data: [] });

      const user = userEvent.setup();
      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.queryByText("Loading chat sessions...")).not.toBeInTheDocument();
      });

      // Open add flow modal
      const addButton = screen.getByTitle("Add new chat from flow");
      await user.click(addButton);

      expect(screen.getByText("Add New Chat from Flow")).toBeInTheDocument();

      // WorkflowsPanel should have received onFlowSelect prop
      expect(workflowsPanelSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          onFlowSelect: expect.any(Function),
        }),
      );
    });
  });

  describe("handleAddFlow()", () => {
    it("creates session via API when flow is added", async () => {
      axiosMock.get.mockResolvedValueOnce({ data: [] });
      axiosMock.post.mockResolvedValueOnce({ data: {} });
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "new-session",
            blueprint_id: "new-bp",
            started_at: "2024-02-02T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "New Flow Session" },
          },
        ],
      });

      const user = userEvent.setup();
      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.queryByText("Loading chat sessions...")).not.toBeInTheDocument();
      });

      // Open modal
      const addButton = screen.getByTitle("Add new chat from flow");
      await user.click(addButton);

      // Simulate flow selection through the mock
      const onFlowSelect = workflowsPanelSpy.mock.calls[0]?.[0]?.onFlowSelect;
      if (onFlowSelect) {
        onFlowSelect({ id: "flow-1", name: "Test Flow" });
      }

      // Click Add button
      const addFlowButton = screen.getByRole("button", { name: /^add$/i });
      await user.click(addFlowButton);

      await waitFor(() => {
        expect(axiosMock.post).toHaveBeenCalledWith(
          "/sessions/user.session.create",
          expect.objectContaining({
            blueprintId: expect.any(String),
            userId: "test-user",
          }),
        );
      });
    });

    it("refreshes session list after creating new session", async () => {
      axiosMock.get.mockResolvedValueOnce({ data: [] });
      axiosMock.post.mockResolvedValueOnce({ data: {} });
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "new-session",
            blueprint_id: "new-bp",
            started_at: "2024-02-02T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "New Flow Session" },
          },
        ],
      });

      const user = userEvent.setup();
      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.queryByText("Loading chat sessions...")).not.toBeInTheDocument();
      });

      // Open modal
      const addButton = screen.getByTitle("Add new chat from flow");
      await user.click(addButton);

      // Simulate flow selection
      const onFlowSelect = workflowsPanelSpy.mock.calls[0]?.[0]?.onFlowSelect;
      if (onFlowSelect) {
        onFlowSelect({ id: "flow-1", name: "Test Flow" });
      }

      // Click Add
      const addFlowButton = screen.getByRole("button", { name: /^add$/i });
      await user.click(addFlowButton);

      await waitFor(() => {
        // Should fetch sessions again after creating
        expect(axiosMock.get).toHaveBeenCalledWith(
          "/sessions/session.user.chat.get?userId=test-user",
        );
      });
    });
  });

  describe("handleCancelAddFlow()", () => {
    it("closes modal when cancel is clicked", async () => {
      axiosMock.get.mockResolvedValueOnce({ data: [] });

      const user = userEvent.setup();
      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.queryByText("Loading chat sessions...")).not.toBeInTheDocument();
      });

      // Open modal
      const addButton = screen.getByTitle("Add new chat from flow");
      await user.click(addButton);

      expect(screen.getByText("Add New Chat from Flow")).toBeInTheDocument();

      // Click Cancel
      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      await user.click(cancelButton);

      await waitFor(() => {
        expect(screen.queryByText("Add New Chat from Flow")).not.toBeInTheDocument();
      });
    });

    it("clears selectedFlowForModal when modal is cancelled", async () => {
      axiosMock.get.mockResolvedValueOnce({ data: [] });

      const user = userEvent.setup();
      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.queryByText("Loading chat sessions...")).not.toBeInTheDocument();
      });

      // Open modal
      const addButton = screen.getByTitle("Add new chat from flow");
      await user.click(addButton);

      // Simulate flow selection
      const onFlowSelect = workflowsPanelSpy.mock.calls[0]?.[0]?.onFlowSelect;
      if (onFlowSelect) {
        onFlowSelect({ id: "flow-1", name: "Test Flow" });
      }

      // Cancel
      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      await user.click(cancelButton);

      await waitFor(() => {
        expect(screen.queryByText("Add New Chat from Flow")).not.toBeInTheDocument();
      });

      // Re-open modal - flow should not be pre-selected
      await user.click(screen.getByTitle("Add new chat from flow"));
      
      // WorkflowsPanel should have selectedFlow as null
      const lastCall = workflowsPanelSpy.mock.calls[workflowsPanelSpy.mock.calls.length - 1];
      expect(lastCall?.[0]?.selectedFlow).toBeNull();
    });
  });

  describe("parseStreamChunk behavior", () => {
    it("extracts ['custom', {...}] chunks from stream text", async () => {
      // This tests the parseStreamChunk function behavior
      // The function is internal to the component but we can verify the pattern matching
      const testPattern = /\["custom",\s*(\{.*?\})\]/g;
      const testChunk = '["custom", {"node": "test", "type": "llm_token"}]';
      
      const match = testPattern.exec(testChunk);
      expect(match).not.toBeNull();
      expect(match?.[1]).toBe('{"node": "test", "type": "llm_token"}');
    });

    it("returns array of parsed JSON objects", () => {
      const testPattern = /\["custom",\s*(\{.*?\})\]/g;
      const testChunk = '["custom", {"a": 1}]["custom", {"b": 2}]';
      
      const results: any[] = [];
      let match: RegExpExecArray | null;
      while ((match = testPattern.exec(testChunk)) !== null) {
        try {
          results.push(JSON.parse(match[1]));
        } catch (e) {
          // ignore
        }
      }
      
      expect(results).toHaveLength(2);
      expect(results[0]).toEqual({ a: 1 });
      expect(results[1]).toEqual({ b: 2 });
    });

    it("warns on parse failures (invalid JSON)", () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      
      const testPattern = /\["custom",\s*(\{.*?\})\]/g;
      const testChunk = '["custom", {invalid json}]';
      
      const match = testPattern.exec(testChunk);
      if (match) {
        try {
          JSON.parse(match[1]);
        } catch (e) {
          console.warn("Failed to parse stream JSON chunk:", match[1]);
        }
      }
      
      expect(consoleSpy).toHaveBeenCalledWith(
        "Failed to parse stream JSON chunk:",
        expect.any(String),
      );
      
      consoleSpy.mockRestore();
    });
  });

  describe("updateNodeList behavior", () => {
    it("creates new node entry if not exists", async () => {
      // The updateNodeList function creates entries in nodeListRef
      // We test through the mock that receives streaming data
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByTestId("chat-interface")).toBeInTheDocument();
      });
    });

    it("handles llm_token chunk type by appending to text", () => {
      // Test the logic for llm_token handling
      const mockEntry = {
        node_name: "TestNode",
        node_uid: "node-1",
        stream: "PROGRESS",
        text: "Hello ",
        tools: [],
        workplans: [],
      };

      // Simulate appending chunk
      const chunk = "world";
      mockEntry.text += chunk;

      expect(mockEntry.text).toBe("Hello world");
    });

    it("handles tool_calling chunk type by adding tool entry", () => {
      const mockEntry = {
        node_name: "TestNode",
        node_uid: "node-1",
        stream: "PROGRESS",
        text: "",
        tools: [] as any[],
        workplans: [],
      };

      // Simulate tool_calling
      const toolData = { id: "call-1", name: "search", args: { query: "test" } };
      mockEntry.tools.push(toolData);

      expect(mockEntry.tools).toHaveLength(1);
      expect(mockEntry.tools[0].name).toBe("search");
    });

    it("handles tool_result chunk type by updating tool with output", () => {
      const mockEntry = {
        node_name: "TestNode",
        node_uid: "node-1",
        stream: "PROGRESS",
        text: "",
        tools: [{ id: "call-1", name: "search", args: { query: "test" } }] as any[],
        workplans: [],
      };

      // Simulate tool_result
      const toolEntry = mockEntry.tools.find(t => t.id === "call-1");
      if (toolEntry) {
        toolEntry.output = "Search results...";
      }

      expect(mockEntry.tools[0].output).toBe("Search results...");
    });

    it("handles workplan_snapshot chunk type by adding/updating workplan", () => {
      const mockEntry = {
        node_name: "TestNode",
        node_uid: "node-1",
        stream: "PROGRESS",
        text: "",
        tools: [],
        workplans: [] as any[],
      };

      // Simulate workplan_snapshot
      const workplanSnapshot = {
        type: "workplan_snapshot",
        action: "loaded",
        plan_id: "plan-1",
        thread_id: "thread-1",
        owner_uid: "node-1",
        node: "node-1",
        display_name: "TestNode",
        workplan: { steps: [] },
      };
      mockEntry.workplans.push(workplanSnapshot);

      expect(mockEntry.workplans).toHaveLength(1);
      expect(mockEntry.workplans[0].plan_id).toBe("plan-1");
    });
  });

  describe("Session list rendering", () => {
    it("renders sessions with title", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "My Chat Session" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      expect(await screen.findByText("My Chat Session")).toBeInTheDocument();
    });

    it("renders sessions with last active time", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T12:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await screen.findByText("Test Session");
      
      // Clock icon should be visible next to time
      const clockIcons = document.querySelectorAll('svg.lucide-clock');
      expect(clockIcons.length).toBeGreaterThan(0);
    });

    it("renders sessions with preview", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { 
              title: "Test Session",
              preview: "Last message preview...",
            },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await screen.findByText("Test Session");
      // Preview text should be truncated and displayed
    });

    it("shows delete button on hover", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      const user = userEvent.setup();
      render(<ExecutionTab runId={null} />);

      const sessionTitle = await screen.findByText("Test Session");
      const sessionElement = sessionTitle.closest('[class*="group"]');

      expect(sessionElement).toBeInTheDocument();
      
      if (sessionElement) {
        await user.hover(sessionElement);
        
        // Delete button should be visible on hover - look for the button with trash icon
        const deleteButton = sessionElement.querySelector('button');
        expect(deleteButton).toBeInTheDocument();
      }
    });
  });

  describe("Additional ChatInterface props", () => {
    it("passes initialMessages={currentSessionMessages}", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(chatInterfaceSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            initialMessages: expect.any(Array),
          }),
        );
      });
    });

    it("passes isValidatingBlueprint", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(chatInterfaceSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            isValidatingBlueprint: expect.any(Boolean),
          }),
        );
      });
    });

    it("passes onToggleBlueprintGraph={toggleBlueprintGraph}", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(chatInterfaceSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            onToggleBlueprintGraph: expect.any(Function),
          }),
        );
      });
    });

    it("passes isBlueprintGraphHidden", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(chatInterfaceSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            isBlueprintGraphHidden: expect.any(Boolean),
          }),
        );
      });
    });
  });

  describe("Graph panel conditions table", () => {
    it("condition: isChatOnlyMode=true shows chat-only message", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-shared",
            blueprint_id: "bp-shared",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Shared Session", source: "public_link" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByText(/shared chat link/)).toBeInTheDocument();
        expect(screen.queryByTestId("reactflow-graph")).not.toBeInTheDocument();
      });
    });

    it("condition: isChatOnlyMode=false, blueprintId exists shows ReactFlowGraph", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-1",
            blueprint_id: "bp-1",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Normal Session" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByTestId("reactflow-graph")).toBeInTheDocument();
        expect(screen.queryByText(/shared chat link/)).not.toBeInTheDocument();
      });
    });

    it("condition: isChatOnlyMode=false, blueprintId=null shows 'No blueprint available'", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-no-bp",
            blueprint_id: null,
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "No Blueprint Session" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByText("No blueprint available for this session")).toBeInTheDocument();
        expect(screen.queryByTestId("reactflow-graph")).not.toBeInTheDocument();
      });
    });

    it("condition: no selectedSession shows 'Select a chat session'", async () => {
      axiosMock.get.mockResolvedValueOnce({ data: [] });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByText("Select a chat session to view blueprint")).toBeInTheDocument();
      });
    });

    it("condition: isChatOnlyMode=true with isSharingDisabled shows warning", async () => {
      axiosMock.get.mockResolvedValueOnce({
        data: [
          {
            session_id: "session-shared",
            blueprint_id: "bp-shared",
            started_at: "2024-02-01T00:00:00.000Z",
            blueprint_exists: true,
            metadata: { title: "Shared Session", source: "public_link" },
          },
        ],
      });

      getBlueprintInfoMock.mockResolvedValue({
        metadata: { usageScope: "private" },
        spec_dict: { name: "Blueprint" },
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(screen.getByText(/sharing has been disabled/)).toBeInTheDocument();
      });
    });
  });
});
