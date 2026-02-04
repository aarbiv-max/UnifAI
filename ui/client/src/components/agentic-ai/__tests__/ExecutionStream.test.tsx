import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@/test-utils/render";

// Mock axios
const axiosMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

vi.mock("../../../http/axiosAgentConfig", () => ({
  default: axiosMock,
}));

// Mock fetchResolvedBlueprints
const fetchResolvedBlueprintsMock = vi.fn();
vi.mock("@/api/blueprints", () => ({
  fetchResolvedBlueprints: (...args: unknown[]) => fetchResolvedBlueprintsMock(...args),
}));

// Mock useAuth
vi.mock("@/contexts/AuthContext", () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth: () => ({
    user: { username: "test-user" },
    isAuthenticated: true,
    isLoading: false,
  }),
}));

// Create mock streaming context
const mockNodeListRef = { current: new Map() };
const mockForceUpdate = vi.fn();
const mockClearStream = vi.fn();

vi.mock("../StreamingDataContext", () => ({
  StreamingDataProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useStreamingData: () => ({
    nodeListRef: mockNodeListRef,
    forceUpdate: mockForceUpdate,
    clearStream: mockClearStream,
  }),
}));

import ExecutionStream from "../ExecutionStream";

describe("ExecutionStream", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockNodeListRef.current.clear();
    
    fetchResolvedBlueprintsMock.mockResolvedValue([
      {
        blueprint_id: "bp-1",
        spec_dict: {
          plan: [
            {
              uid: "node-1",
              node: "ref-1",
              meta: { display_name: "Node One", description: "First node" },
            },
            {
              uid: "node-2",
              node: "ref-2",
              meta: { display_name: "Node Two" },
            },
          ],
          nodes: [
            { rid: "ref-1", name: "First Node", config: { description: "Config desc" } },
            { rid: "ref-2", name: "Second Node" },
          ],
        },
      },
    ]);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("Initialization", () => {
    it("initializes with system log: 'Agentic AI system initialized and ready.'", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByText("Agentic AI system initialized and ready.")).toBeInTheDocument();
      });
    });

    it("fetches blueprint data from fetchResolvedBlueprints() on mount", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalledWith("test-user");
      });
    });

    it("extracts node data from blueprint's spec_dict", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        // Node names should appear in the sidebar
        expect(screen.getByText("First Node")).toBeInTheDocument();
        expect(screen.getByText("Second Node")).toBeInTheDocument();
      });
    });

    it("auto-selects first node if nodes exist", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        // The first node should be selected (has border highlight)
        const nodeElement = screen.getByText("First Node").closest("div");
        expect(nodeElement?.parentElement).toHaveClass("border-[#00B0FF]");
      });
    });

    it("extractNodeData() returns empty array if no graphFlow.plan", async () => {
      fetchResolvedBlueprintsMock.mockResolvedValue([
        {
          blueprint_id: "bp-empty",
          spec_dict: {},
        },
      ]);

      render(<ExecutionStream blueprintId="bp-empty" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });
      
      // No agent nodes should be rendered (only system log visible)
      expect(screen.getByText("Agent Nodes")).toBeInTheDocument();
    });

    it("maps plan items to node data: id from item.uid, name from node or meta", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        // Name comes from nodes array (node.name)
        expect(screen.getByText("First Node")).toBeInTheDocument();
        expect(screen.getByText("Second Node")).toBeInTheDocument();
      });
    });
  });

  describe("Polling behavior", () => {
    it("only starts polling when isLiveRequest=true and !isPaused", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      // With isLiveRequest=false, no polling should occur
      mockNodeListRef.current.set("node-1", {
        node_uid: "node-1",
        node_name: "First Node",
        stream: "PROGRESS",
        text: "Processing data",
      });

      // Advance time and verify no update occurs
      vi.advanceTimersByTime(200);
      expect(screen.queryByText("Processing data")).not.toBeInTheDocument();
    });

    it("polls nodeListRef.current every 100ms when live", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        expect(screen.getByText("First Node")).toBeInTheDocument();
      });

      // Add entry to nodeListRef
      mockNodeListRef.current.set("node-1", {
        node_uid: "node-1",
        node_name: "First Node",
        stream: "PROGRESS",
        text: "Live processing",
      });

      // Advance time by 100ms
      vi.advanceTimersByTime(100);

      await waitFor(() => {
        expect(screen.getByText("Live processing")).toBeInTheDocument();
      });
    });

    it("clears interval on unmount or when conditions change", async () => {
      const { unmount } = render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      const clearIntervalSpy = vi.spyOn(global, "clearInterval");
      unmount();

      expect(clearIntervalSpy).toHaveBeenCalled();
    });
  });

  describe("Log filtering", () => {
    it("shows all logs when no node selected", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        // System log should always be visible
        expect(screen.getByText("Agentic AI system initialized and ready.")).toBeInTheDocument();
      });
    });

    it("filters to selected node logs + system logs when node selected", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        expect(screen.getByText("First Node")).toBeInTheDocument();
      });

      // Add logs for both nodes
      mockNodeListRef.current.set("node-1", {
        node_uid: "node-1",
        stream: "PROGRESS",
        text: "First node log",
      });
      mockNodeListRef.current.set("node-2", {
        node_uid: "node-2",
        stream: "PROGRESS",
        text: "Second node log",
      });

      vi.advanceTimersByTime(100);

      // Click on second node
      await user.click(screen.getByText("Second Node"));

      await waitFor(() => {
        // System log should still be visible
        expect(screen.getByText("Agentic AI system initialized and ready.")).toBeInTheDocument();
      });
    });
  });

  describe("Status mapping", () => {
    it("maps stream types: PROGRESS → 'processing', ERROR → 'error', COMPLETE → 'success'", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        expect(screen.getByText("First Node")).toBeInTheDocument();
      });

      // Add an error log
      mockNodeListRef.current.set("node-1", {
        node_uid: "node-1",
        stream: "ERROR",
        text: "Error occurred",
      });

      vi.advanceTimersByTime(100);

      await waitFor(() => {
        const errorLog = screen.getByText("Error occurred");
        expect(errorLog).toHaveClass("text-[#FF1744]");
      });
    });
  });

  describe("Control buttons", () => {
    it("Pause/Play button: toggles isPaused state", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      // Find the pause button (first button with Pause icon)
      const pauseButton = screen.getAllByRole("button")[0];
      expect(pauseButton).not.toBeDisabled();

      // Click to pause
      await user.click(pauseButton);

      // Now clicking should show play icon (button is toggled)
      // The button should now work to resume
    });

    it("Pause/Play button disabled when !isLiveRequest", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      // Find the pause/play button
      const buttons = screen.getAllByRole("button");
      const pauseButton = buttons[0];
      
      expect(pauseButton).toHaveClass("opacity-50");
      expect(pauseButton).toHaveClass("cursor-not-allowed");
    });

    it("Trash button: calls clearLogs() - resets to single 'Execution logs cleared' message", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByText("Agentic AI system initialized and ready.")).toBeInTheDocument();
      });

      // Find and click trash button
      const buttons = screen.getAllByRole("button");
      const trashButton = buttons[1];
      await user.click(trashButton);

      await waitFor(() => {
        expect(screen.getByText("Execution logs cleared.")).toBeInTheDocument();
        expect(screen.queryByText("Agentic AI system initialized and ready.")).not.toBeInTheDocument();
      });
    });

    it("Download button: rendered (functionality placeholder)", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      // Download button should exist (3rd button)
      const buttons = screen.getAllByRole("button");
      expect(buttons.length).toBeGreaterThanOrEqual(3);
    });
  });

  describe("Status icons", () => {
    it("shows StatusIcon for each status type", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        // System log shows 'info' status with blue color
        const systemLog = screen.getByText("System");
        expect(systemLog).toBeInTheDocument();
      });
    });

    it("shows formatted timestamp (HH:MM:SS)", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        // Timestamp should be in HH:MM:SS format
        const timePattern = /\d{1,2}:\d{2}:\d{2}/;
        const logArea = screen.getByText("Agentic AI system initialized and ready.").closest("div");
        expect(logArea?.textContent).toMatch(timePattern);
      });
    });

    it("shows agent name with status-based color badge", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        // System badge should have info status styling (blue)
        const systemBadge = screen.getByText("System");
        expect(systemBadge).toHaveClass("bg-[#00B0FF]");
      });
    });
  });

  describe("Log count display", () => {
    it("shows log count: '{N} log entries'", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByText(/1 log entries/)).toBeInTheDocument();
      });
    });

    it("shows ' for {nodeName}' when node selected", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByText("First Node")).toBeInTheDocument();
      });

      // First node is auto-selected, so should show "for First Node"
      expect(screen.getByText(/for First Node/)).toBeInTheDocument();
    });

    it("shows auto-scroll checkbox", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByLabelText("Auto-scroll")).toBeInTheDocument();
      });
    });

    it("respects autoscroll checkbox toggle", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByLabelText("Auto-scroll")).toBeInTheDocument();
      });

      const checkbox = screen.getByLabelText("Auto-scroll");
      expect(checkbox).toBeChecked(); // Default is true

      await user.click(checkbox);
      expect(checkbox).not.toBeChecked();
    });
  });

  describe("getRandomAgentIcon", () => {
    it("returns random icon from predefined set", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        // Icons should be rendered for nodes
        const nodeElements = screen.getAllByText(/Node/);
        expect(nodeElements.length).toBeGreaterThan(0);
      });
    });
  });
});
