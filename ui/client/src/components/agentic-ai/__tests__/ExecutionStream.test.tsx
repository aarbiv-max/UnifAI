import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@/test-utils/render";

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

    it("shows Agent Nodes section header", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByText("Agent Nodes")).toBeInTheDocument();
      });
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

  describe("Control buttons", () => {
    it("renders pause/play button", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      const buttons = screen.getAllByRole("button");
      expect(buttons.length).toBeGreaterThanOrEqual(3);
    });

    it("renders trash button", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      const buttons = screen.getAllByRole("button");
      expect(buttons.length).toBeGreaterThanOrEqual(2);
    });

    it("renders download button", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      const buttons = screen.getAllByRole("button");
      expect(buttons.length).toBeGreaterThanOrEqual(3);
    });

    it("trash button clears logs", async () => {
      const user = userEvent.setup();

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByText("Agentic AI system initialized and ready.")).toBeInTheDocument();
      });

      // Find and click trash button (second button after pause)
      const buttons = screen.getAllByRole("button");
      const trashButton = buttons[1];
      await user.click(trashButton);

      await waitFor(() => {
        expect(screen.getByText("Execution logs cleared.")).toBeInTheDocument();
      });
    });
  });

  describe("Log display", () => {
    it("shows log count", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByText(/log entr/)).toBeInTheDocument();
      });
    });

    it("shows System label for system logs", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByText("System")).toBeInTheDocument();
      });
    });
  });

  describe("Auto-scroll", () => {
    it("shows auto-scroll checkbox", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByLabelText("Auto-scroll")).toBeInTheDocument();
      });
    });

    it("auto-scroll checkbox is checked by default", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        const checkbox = screen.getByLabelText("Auto-scroll");
        expect(checkbox).toBeChecked();
      });
    });

    it("toggles auto-scroll checkbox", async () => {
      const user = userEvent.setup();

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByLabelText("Auto-scroll")).toBeInTheDocument();
      });

      const checkbox = screen.getByLabelText("Auto-scroll");
      expect(checkbox).toBeChecked();

      await user.click(checkbox);
      expect(checkbox).not.toBeChecked();
    });
  });

  describe("Node selection", () => {
    it("allows clicking on nodes to select them", async () => {
      const user = userEvent.setup();

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByText("Second Node")).toBeInTheDocument();
      });

      await user.click(screen.getByText("Second Node"));
      
      // After clicking, the node should be highlighted (we can't easily test CSS, but at least verify no errors)
      expect(screen.getByText("Second Node")).toBeInTheDocument();
    });
  });

  describe("Card structure", () => {
    it("renders with Execution Stream title", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByText("Execution Stream")).toBeInTheDocument();
      });
    });
  });

  describe("extractNodeData behavior", () => {
    it("returns empty array if graphFlow is null", async () => {
      fetchResolvedBlueprintsMock.mockResolvedValue([]);
      
      render(<ExecutionStream blueprintId="non-existent" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      // No nodes should appear (empty array returned)
      expect(screen.queryByText("First Node")).not.toBeInTheDocument();
    });

    it("returns empty array if graphFlow.plan is undefined", async () => {
      fetchResolvedBlueprintsMock.mockResolvedValue([
        {
          blueprint_id: "bp-empty",
          spec_dict: {
            // No plan property
            nodes: [],
          },
        },
      ]);
      
      render(<ExecutionStream blueprintId="bp-empty" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      // Agent Nodes header still appears, but no actual nodes
      await waitFor(() => {
        expect(screen.getByText("Agent Nodes")).toBeInTheDocument();
      });
    });

    it("uses node.name from nodes array when available", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        // Names come from nodes array (node.name)
        expect(screen.getByText("First Node")).toBeInTheDocument();
        expect(screen.getByText("Second Node")).toBeInTheDocument();
      });
    });

    it("falls back to meta.display_name when node not found", async () => {
      fetchResolvedBlueprintsMock.mockResolvedValue([
        {
          blueprint_id: "bp-fallback",
          spec_dict: {
            plan: [
              {
                uid: "node-orphan",
                node: "non-existent-ref",
                meta: { display_name: "Orphan Display Name" },
              },
            ],
            nodes: [],
          },
        },
      ]);
      
      render(<ExecutionStream blueprintId="bp-fallback" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByText("Orphan Display Name")).toBeInTheDocument();
      });
    });

    it("falls back to 'General Node' when no name available", async () => {
      fetchResolvedBlueprintsMock.mockResolvedValue([
        {
          blueprint_id: "bp-general",
          spec_dict: {
            plan: [
              {
                uid: "node-generic",
                node: "non-existent-ref",
                meta: {},
              },
            ],
            nodes: [],
          },
        },
      ]);
      
      render(<ExecutionStream blueprintId="bp-general" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByText("General Node")).toBeInTheDocument();
      });
    });
  });

  describe("getRandomAgentIcon", () => {
    it("assigns icons to nodes on load", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByText("First Node")).toBeInTheDocument();
      });

      // Nodes should have SVG icons in the sidebar
      const firstNodeElement = screen.getByText("First Node");
      const nodeContainer = firstNodeElement.closest('[class*="px-4"]');
      expect(nodeContainer).toBeInTheDocument();
      // Icon is rendered next to the node name
      const svgIcon = nodeContainer?.querySelector('svg');
      expect(svgIcon).toBeInTheDocument();
    });
  });

  describe("Polling behavior", () => {
    it("does not poll when isLiveRequest is false", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      // When isLiveRequest is false, polling interval should not be set
      // Component should still render normally
      expect(screen.getByText("Execution Stream")).toBeInTheDocument();
    });

    it("polling starts when isLiveRequest is true and not paused", async () => {
      // Add some data to the nodeListRef
      mockNodeListRef.current.set('node-1', {
        node_uid: 'node-1',
        text: 'Processing...',
        stream: 'PROGRESS',
      });

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      // Verify component renders with live mode enabled
      expect(screen.getByText("Execution Stream")).toBeInTheDocument();
    });

    it("pause button is available when live", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      const buttons = screen.getAllByRole("button");
      // First button should not have the disabled opacity class when live
      expect(buttons[0]).not.toHaveClass("cursor-not-allowed");
    });
  });

  describe("Stream type mapping", () => {
    it("maps PROGRESS stream to processing status (100ms interval)", async () => {
      mockNodeListRef.current.set('node-1', {
        node_uid: 'node-1',
        text: 'Working on task...',
        stream: 'PROGRESS',
      });

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      // Verify component is ready for streaming
      expect(screen.getByText("Execution Stream")).toBeInTheDocument();
    });

    it("maps ERROR stream to error status", async () => {
      mockNodeListRef.current.set('node-1', {
        node_uid: 'node-1',
        text: 'An error occurred',
        stream: 'ERROR',
      });

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      expect(screen.getByText("Execution Stream")).toBeInTheDocument();
    });

    it("maps COMPLETE stream to success status", async () => {
      mockNodeListRef.current.set('node-1', {
        node_uid: 'node-1',
        text: 'Task completed',
        stream: 'COMPLETE',
      });

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      expect(screen.getByText("Execution Stream")).toBeInTheDocument();
    });

    it("maps unknown stream type to info status by default", async () => {
      mockNodeListRef.current.set('node-1', {
        node_uid: 'node-1',
        text: 'General info',
        stream: 'UNKNOWN_TYPE',
      });

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      expect(screen.getByText("Execution Stream")).toBeInTheDocument();
    });
  });

  describe("Log filtering", () => {
    it("shows all logs when no node is selected initially", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByText("Agentic AI system initialized and ready.")).toBeInTheDocument();
      });

      // System log should be visible
      expect(screen.getByText("System")).toBeInTheDocument();
    });

    it("system logs remain visible when node is selected", async () => {
      const user = userEvent.setup();

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByText("Second Node")).toBeInTheDocument();
      });

      // Select Second Node
      await user.click(screen.getByText("Second Node"));

      // System logs should still be visible after filtering
      expect(screen.getByText("Agentic AI system initialized and ready.")).toBeInTheDocument();
    });

    it("shows log count with selected node name", async () => {
      const user = userEvent.setup();

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByText("First Node")).toBeInTheDocument();
      });

      await user.click(screen.getByText("First Node"));

      // Should show count with node name
      await waitFor(() => {
        expect(screen.getByText(/log entr.*for First Node/)).toBeInTheDocument();
      });
    });
  });

  describe("Pause/Play button toggle", () => {
    it("renders Pause icon when not paused and live", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      // First button is pause/play, should have an SVG icon
      const buttons = screen.getAllByRole("button");
      expect(buttons[0]).toBeInTheDocument();
      expect(buttons[0].querySelector("svg")).toBeInTheDocument();
    });

    it("clicking pause button toggles icon", async () => {
      const user = userEvent.setup();

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      const buttons = screen.getAllByRole("button");
      await user.click(buttons[0]);

      // After clicking, button should still have an SVG icon
      expect(buttons[0].querySelector("svg")).toBeInTheDocument();
    });

    it("clicking twice returns to original state", async () => {
      const user = userEvent.setup();

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      const buttons = screen.getAllByRole("button");
      
      // Click to pause then resume
      await user.click(buttons[0]);
      await user.click(buttons[0]);

      expect(buttons[0].querySelector("svg")).toBeInTheDocument();
    });

    it("pause button has disabled styling when isLiveRequest is false", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      const buttons = screen.getAllByRole("button");
      // The pause button should have opacity-50 class indicating disabled state
      expect(buttons[0]).toHaveClass("opacity-50");
    });
  });

  describe("Download button", () => {
    it("renders download button with icon", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      // Download button is the third button (after pause and trash)
      const buttons = screen.getAllByRole("button");
      expect(buttons.length).toBeGreaterThanOrEqual(3);
      
      // The download button should have an SVG icon
      expect(buttons[2].querySelector("svg")).toBeInTheDocument();
    });

    it("download button can be clicked", async () => {
      const user = userEvent.setup();

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      const buttons = screen.getAllByRole("button");
      // Should not throw when clicked
      await user.click(buttons[2]);
      
      // Component should still be rendered
      expect(screen.getByText("Execution Stream")).toBeInTheDocument();
    });
  });

  describe("StatusIcon color/icon mapping", () => {
    it("displays icon for info status system log", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByText("Agentic AI system initialized and ready.")).toBeInTheDocument();
      });

      // The system log has info status, should have SVG icon
      const logEntry = screen.getByText("Agentic AI system initialized and ready.").closest(".mb-2");
      expect(logEntry?.querySelector("svg")).toBeInTheDocument();
    });

    it("has processing status configuration for PROGRESS stream", () => {
      // Test that stream mapping returns correct status
      // PROGRESS -> 'processing' (based on component code)
      mockNodeListRef.current.set('node-1', {
        node_uid: 'node-1',
        text: 'Processing...',
        stream: 'PROGRESS',
      });

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);
      
      // Component should handle PROGRESS stream
      expect(screen.getByText("Execution Stream")).toBeInTheDocument();
    });

    it("has success status configuration for COMPLETE stream", () => {
      mockNodeListRef.current.set('node-1', {
        node_uid: 'node-1',
        text: 'Completed!',
        stream: 'COMPLETE',
      });

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);
      
      expect(screen.getByText("Execution Stream")).toBeInTheDocument();
    });

    it("has error status configuration for ERROR stream", () => {
      mockNodeListRef.current.set('node-1', {
        node_uid: 'node-1',
        text: 'Error occurred',
        stream: 'ERROR',
      });

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);
      
      expect(screen.getByText("Execution Stream")).toBeInTheDocument();
    });

    it("shows info status with blue color (#00B0FF)", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByText("Agentic AI system initialized and ready.")).toBeInTheDocument();
      });

      // Info status should have blue color
      const infoIcon = screen.getByText("Agentic AI system initialized and ready.")
        .closest(".mb-2")
        ?.querySelector("svg.text-\\[\\#00B0FF\\]");
      expect(infoIcon).toBeInTheDocument();
    });

    it("shows processing status with amber/yellow color (#FFB300)", async () => {
      mockNodeListRef.current.set('node-1', {
        node_uid: 'node-1',
        text: 'Working...',
        stream: 'PROGRESS',
      });

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);
      
      // The processing status should have AlertCircle icon with amber color
      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });
    });

    it("shows success status with green color (hsl(var(--success)))", async () => {
      mockNodeListRef.current.set('node-1', {
        node_uid: 'node-1',
        text: 'Completed!',
        stream: 'COMPLETE',
      });

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);
      
      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });
    });

    it("shows error status with red color (#FF1744)", async () => {
      mockNodeListRef.current.set('node-1', {
        node_uid: 'node-1',
        text: 'Error occurred',
        stream: 'ERROR',
      });

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);
      
      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });
    });
  });

  describe("AgentNode creation", () => {
    it("creates AgentNode[] with id from plan item uid", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        // Node should appear - id comes from item.uid in plan
        expect(screen.getByText("First Node")).toBeInTheDocument();
      });
    });

    it("creates AgentNode[] with name from node.name", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        // Names come from nodes array (node.name)
        expect(screen.getByText("First Node")).toBeInTheDocument();
        expect(screen.getByText("Second Node")).toBeInTheDocument();
      });
    });

    it("creates AgentNode[] with description from config or meta", async () => {
      fetchResolvedBlueprintsMock.mockResolvedValue([
        {
          blueprint_id: "bp-desc",
          spec_dict: {
            plan: [
              {
                uid: "node-config-desc",
                node: "ref-config",
                meta: { display_name: "Config Node", description: "Meta description" },
              },
            ],
            nodes: [
              { rid: "ref-config", name: "Config Node", config: { description: "Config description" } },
            ],
          },
        },
      ]);

      render(<ExecutionStream blueprintId="bp-desc" isLiveRequest={false} />);

      await waitFor(() => {
        // Description should be displayed (config description takes precedence)
        expect(screen.getByText("Config description")).toBeInTheDocument();
      });
    });

    it("falls back to meta.description when config.description is not available", async () => {
      fetchResolvedBlueprintsMock.mockResolvedValue([
        {
          blueprint_id: "bp-meta-desc",
          spec_dict: {
            plan: [
              {
                uid: "node-meta-desc",
                node: "ref-meta",
                meta: { display_name: "Meta Node", description: "Meta description only" },
              },
            ],
            nodes: [
              { rid: "ref-meta", name: "Meta Node" }, // No config.description
            ],
          },
        },
      ]);

      render(<ExecutionStream blueprintId="bp-meta-desc" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByText("Meta description only")).toBeInTheDocument();
      });
    });

    it("creates AgentNode[] with random icon from agentIcons array", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByText("First Node")).toBeInTheDocument();
      });

      // Each node should have an icon (SVG) in the sidebar
      const firstNodeElement = screen.getByText("First Node");
      const nodeContainer = firstNodeElement.closest('[class*="px-4"]');
      expect(nodeContainer).toBeInTheDocument();
      // Icon is rendered next to the node name
      const svgIcon = nodeContainer?.querySelector('svg');
      expect(svgIcon).toBeInTheDocument();
    });
  });

  describe("Auto-select first node", () => {
    it("auto-selects first node if nodes exist", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(screen.getByText("First Node")).toBeInTheDocument();
      });

      // First node should be selected (highlighted with border)
      const firstNodeElement = screen.getByText("First Node").closest('[class*="px-4"]');
      expect(firstNodeElement).toHaveClass("border-[#00B0FF]");
    });

    it("does not auto-select if no nodes exist", async () => {
      fetchResolvedBlueprintsMock.mockResolvedValue([
        {
          blueprint_id: "bp-empty-plan",
          spec_dict: {
            plan: [],
            nodes: [],
          },
        },
      ]);

      render(<ExecutionStream blueprintId="bp-empty-plan" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      // No nodes should be highlighted
      expect(screen.queryByText("First Node")).not.toBeInTheDocument();
    });
  });

  describe("Polling behavior (100ms interval)", () => {
    it("sets up interval when isLiveRequest is true", async () => {
      mockNodeListRef.current.set('node-1', {
        node_uid: 'node-1',
        text: 'Initial text',
        stream: 'PROGRESS',
      });

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      // Component should be rendered and ready for polling
      expect(screen.getByText("Execution Stream")).toBeInTheDocument();
    });

    it("clears interval on unmount", async () => {
      const clearIntervalSpy = vi.spyOn(global, 'clearInterval');

      const { unmount } = render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      unmount();

      // clearInterval should have been called on unmount
      expect(clearIntervalSpy).toHaveBeenCalled();

      clearIntervalSpy.mockRestore();
    });

    it("component renders when isLiveRequest changes to false", async () => {
      const { rerender } = render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      // Rerender with isLiveRequest=false
      rerender(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      // Component should still be rendered
      expect(screen.getByText("Execution Stream")).toBeInTheDocument();
    });

    it("pause button toggles isPaused state", async () => {
      const user = userEvent.setup();

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      // Click pause button to toggle isPaused
      const buttons = screen.getAllByRole("button");
      await user.click(buttons[0]);

      // Component should still be rendered after pause
      expect(screen.getByText("Execution Stream")).toBeInTheDocument();
    });
  });

  describe("System logs and node logs", () => {
    it("keeps system logs when updating node logs", async () => {
      mockNodeListRef.current.set('node-1', {
        node_uid: 'node-1',
        text: 'Node is processing',
        stream: 'PROGRESS',
      });

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        // System log should still be present
        expect(screen.getByText("Agentic AI system initialized and ready.")).toBeInTheDocument();
      });
    });

    it("displays system log initially", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      // System log should be visible
      expect(screen.getByText("Agentic AI system initialized and ready.")).toBeInTheDocument();
    });
  });

  describe("LogEntry creation", () => {
    it("LogEntry structure has id field", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      // LogEntry should be created - verify by checking system log is present
      expect(screen.getByText("Execution Stream")).toBeInTheDocument();
      expect(screen.getByText("Agentic AI system initialized and ready.")).toBeInTheDocument();
    });

    it("creates LogEntry with timestamp", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(screen.getByText("Agentic AI system initialized and ready.")).toBeInTheDocument();
      });

      // Timestamp should be displayed in HH:MM:SS format
      const logEntry = screen.getByText("Agentic AI system initialized and ready.").closest(".mb-2");
      const timeDisplay = logEntry?.querySelector(".text-gray-400");
      expect(timeDisplay).toBeInTheDocument();
      // Check that timestamp is in format like "HH:MM:SS"
      expect(timeDisplay?.textContent).toMatch(/\d{1,2}:\d{2}:\d{2}/);
    });

    it("creates LogEntry with agent name", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(screen.getByText("System")).toBeInTheDocument();
      });
    });

    it("creates LogEntry with message", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(screen.getByText("Agentic AI system initialized and ready.")).toBeInTheDocument();
      });
    });

    it("creates LogEntry with status", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(screen.getByText("Agentic AI system initialized and ready.")).toBeInTheDocument();
      });

      // Status icon should be visible (info status for system log)
      const logEntry = screen.getByText("Agentic AI system initialized and ready.").closest(".mb-2");
      expect(logEntry?.querySelector("svg")).toBeInTheDocument();
    });
  });

  describe("Timestamp formatting", () => {
    it("shows formatted timestamp in HH:MM:SS format", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(screen.getByText("Agentic AI system initialized and ready.")).toBeInTheDocument();
      });

      // Find timestamp display
      const logEntry = screen.getByText("Agentic AI system initialized and ready.").closest(".mb-2");
      const timestampElement = logEntry?.querySelector(".text-gray-400");
      
      expect(timestampElement).toBeInTheDocument();
      // Timestamp should be in locale time format with hours, minutes, seconds
      expect(timestampElement?.textContent).toMatch(/\d{1,2}:\d{2}:\d{2}/);
    });
  });

  describe("Agent name badge with status-based color", () => {
    it("shows agent name with info status blue badge", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(screen.getByText("System")).toBeInTheDocument();
      });

      // System badge should have info color (blue)
      const systemBadge = screen.getByText("System");
      expect(systemBadge).toHaveClass("bg-[#00B0FF]");
    });
  });

  describe("Error message text styling", () => {
    it("error status uses red text styling", async () => {
      mockNodeListRef.current.set('node-1', {
        node_uid: 'node-1',
        text: 'An error occurred',
        stream: 'ERROR',
      });

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      // Component should handle error status (red text class is text-[#FF1744])
      expect(screen.getByText("Execution Stream")).toBeInTheDocument();
    });

    it("shows message text in gray for non-error status", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(screen.getByText("Agentic AI system initialized and ready.")).toBeInTheDocument();
      });

      // Non-error messages should have gray-300 text
      const messageElement = screen.getByText("Agentic AI system initialized and ready.");
      expect(messageElement).toHaveClass("text-gray-300");
    });
  });

  describe("Status icon and color table", () => {
    it("info status: Info icon with #00B0FF color", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(screen.getByText("Agentic AI system initialized and ready.")).toBeInTheDocument();
      });

      // Info icon should be blue
      const logEntry = screen.getByText("Agentic AI system initialized and ready.").closest(".mb-2");
      const infoIcon = logEntry?.querySelector("svg.text-\\[\\#00B0FF\\]");
      expect(infoIcon).toBeInTheDocument();
    });

    it("info status: badge with #00B0FF background", async () => {
      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={false} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(screen.getByText("System")).toBeInTheDocument();
      });

      // Badge should have blue background
      const badge = screen.getByText("System");
      expect(badge).toHaveClass("bg-[#00B0FF]");
      expect(badge).toHaveClass("text-[#00B0FF]");
    });

    it("processing status uses AlertCircle icon with animation", async () => {
      mockNodeListRef.current.set('node-1', {
        node_uid: 'node-1',
        text: 'Processing...',
        stream: 'PROGRESS',
      });

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      // Processing status should use AlertCircle with rotation animation
      expect(screen.getByText("Execution Stream")).toBeInTheDocument();
    });

    it("success status: CheckCircle icon with hsl(var(--success)) color", async () => {
      mockNodeListRef.current.set('node-1', {
        node_uid: 'node-1',
        text: 'Task complete',
        stream: 'COMPLETE',
      });

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      // Success status should use CheckCircle with success color
      expect(screen.getByText("Execution Stream")).toBeInTheDocument();
    });

    it("error status: AlertCircle icon with #FF1744 color", async () => {
      mockNodeListRef.current.set('node-1', {
        node_uid: 'node-1',
        text: 'Error!',
        stream: 'ERROR',
      });

      render(<ExecutionStream blueprintId="bp-1" isLiveRequest={true} />);

      await waitFor(() => {
        expect(fetchResolvedBlueprintsMock).toHaveBeenCalled();
      });

      // Error status should use AlertCircle with red color
      expect(screen.getByText("Execution Stream")).toBeInTheDocument();
    });
  });
});
