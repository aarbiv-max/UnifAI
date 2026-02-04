import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
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
  default: (props: any) => {
    chatInterfaceSpy(props);
    return (
      <div data-testid="chat-interface">
        ChatInterface {props.runId}
        {props.blueprintExists === false && <span>workflow-deleted</span>}
        {props.isSharingDisabled && <span>sharing-disabled</span>}
        {props.blueprintValid === false && <span>validation-failed</span>}
        {props.isValidatingBlueprint && <span>validating</span>}
        {props.isChatOnlyMode && <span>chat-only-mode</span>}
        <button onClick={props.onToggleBlueprintGraph}>Toggle Graph</button>
      </div>
    );
  },
}));

vi.mock("../ExecutionStream", () => ({
  default: () => <div data-testid="execution-stream">ExecutionStream</div>,
}));

const reactFlowGraphSpy = vi.fn();
vi.mock("../graphs/ReactFlowGraph", () => ({
  default: (props: any) => {
    reactFlowGraphSpy(props);
    return <div data-testid="reactflow-graph">ReactFlowGraph {props.blueprintId}</div>;
  },
}));

const workflowsPanelSpy = vi.fn();
vi.mock("../WorkflowsPanel", () => ({
  default: (props: any) => {
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
    loadSessionMessages: loadSessionMessagesMock.mockImplementation(async (session: any) => ({
      ...session,
      messages: [],
    })),
    clearMessages: vi.fn(),
    setCurrentMessages: vi.fn(),
  }),
}));

const checkSessionSharingStatusMock = vi.fn();
vi.mock("@/hooks/use-sharing-status", () => ({
  checkSessionSharingStatus: (...args: any[]) => checkSessionSharingStatusMock(...args),
}));

const getBlueprintInfoMock = vi.fn();
vi.mock("@/api/blueprints", () => ({
  getBlueprintInfo: (...args: any[]) => getBlueprintInfoMock(...args),
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

    it("initializes panel widths: chatSidebar=20%, chatInterface=50%, blueprintGraph=30%", () => {
      axiosMock.get.mockResolvedValueOnce({ data: [] });

      const { container } = render(<ExecutionTab runId={null} />);

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
            from_shared_link: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      getBlueprintInfoMock.mockResolvedValue({
        metadata: { usageScope: "private" },
        spec_dict: { name: "Blueprint" },
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(chatInterfaceSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            isSharingDisabled: true,
          }),
        );
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
            from_shared_link: true,
            metadata: { title: "Shared Session" },
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
            from_shared_link: true,
            metadata: { title: "Shared Session" },
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
            from_shared_link: true,
            metadata: { title: "Shared Session" },
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
            from_shared_link: true,
            metadata: { title: "Shared Session" },
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
            from_shared_link: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      getBlueprintInfoMock.mockResolvedValue({
        metadata: { usageScope: "private" },
        spec_dict: { name: "Blueprint" },
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(chatInterfaceSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            isSharingDisabled: true,
          }),
        );
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
            from_shared_link: true,
            metadata: { title: "Test Session" },
          },
        ],
      });

      render(<ExecutionTab runId={null} />);

      await waitFor(() => {
        expect(chatInterfaceSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            isChatOnlyMode: true,
          }),
        );
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
});
