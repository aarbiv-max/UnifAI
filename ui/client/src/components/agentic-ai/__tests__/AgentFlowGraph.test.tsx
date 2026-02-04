import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@/test-utils/render";
import type { FlowObject } from "../graphs/interfaces";

const mockFlow = vi.hoisted(
  () =>
    ({
      id: "flow-1",
      name: "Sample Flow",
      description: "Test flow",
      icon: null,
      flow: { nodes: [], edges: [] },
    }) as FlowObject,
);

const differentFlow = vi.hoisted(
  () =>
    ({
      id: "flow-2",
      name: "Different Flow",
      description: "Another flow",
      icon: null,
      flow: { nodes: [], edges: [] },
    }) as FlowObject,
);

const workflowsPanelSpy = vi.fn();

vi.mock("../WorkflowsPanel", () => ({
  default: (props: any) => {
    workflowsPanelSpy(props);
    const nodeCount = props.selectedFlow?.flow?.nodes?.length ?? 0;
    const edgeCount = props.selectedFlow?.flow?.edges?.length ?? 0;

    return (
      <div data-testid="workflows-panel">
        <div data-testid="graph-canvas">
          Nodes: {nodeCount} Edges: {edgeCount}
        </div>
        <button type="button" onClick={() => props.onFlowSelect?.(mockFlow)}>
          Select Flow
        </button>
        <button type="button" onClick={() => props.onFlowSelect?.(null)}>
          Clear Selection
        </button>
        <button type="button" onClick={() => props.onFlowDelete?.(mockFlow)}>
          Delete Selected Flow
        </button>
        <button type="button" onClick={() => props.onFlowDelete?.(differentFlow)}>
          Delete Different Flow
        </button>
        <button
          type="button"
          onClick={() =>
            props.onValidationChange?.(false, { errors: ["invalid"] }, false)
          }
        >
          Trigger Validation Error
        </button>
        <button
          type="button"
          onClick={() =>
            props.onValidationChange?.(true, null, false)
          }
        >
          Trigger Validation Success
        </button>
      </div>
    );
  },
}));

vi.mock("../StreamingDataContext", () => ({
  StreamingDataProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="streaming-data-provider">{children}</div>
  ),
  useStreamingData: () => ({
    nodeListRef: { current: new Map() },
    forceUpdate: vi.fn(),
    clearStream: vi.fn(),
  }),
}));

vi.mock("reactflow", () => ({
  ReactFlowProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="reactflow-provider">{children}</div>
  ),
}));

import AgentFlowGraph from "../AgentFlowGraph";

describe("AgentFlowGraph", () => {
  beforeEach(() => {
    workflowsPanelSpy.mockClear();
  });

  describe("Rendering", () => {
    it("renders Card with title 'Agent Workflow Visualization'", () => {
      render(
        <AgentFlowGraph
          selectedFlow={null}
          setSelectedFlow={vi.fn()}
        />,
      );

      expect(
        screen.getByText("Agent Workflow Visualization"),
      ).toBeInTheDocument();
    });

    it("wraps content in StreamingDataProvider", () => {
      render(
        <AgentFlowGraph
          selectedFlow={null}
          setSelectedFlow={vi.fn()}
        />,
      );

      expect(screen.getByTestId("streaming-data-provider")).toBeInTheDocument();
    });

    it("wraps content in ReactFlowProvider", () => {
      render(
        <AgentFlowGraph
          selectedFlow={null}
          setSelectedFlow={vi.fn()}
        />,
      );

      expect(screen.getByTestId("reactflow-provider")).toBeInTheDocument();
    });

    it("sets CardContent height to '73.5vh'", () => {
      const { container } = render(
        <AgentFlowGraph
          selectedFlow={null}
          setSelectedFlow={vi.fn()}
        />,
      );

      // Find the CardContent element by checking for the height style
      // Use getAttribute to check the raw style value since jsdom computes vh to px
      const cardContent = container.querySelector('[style*="height"]');
      expect(cardContent?.getAttribute('style')).toContain('height: 73.5vh');
    });
  });

  describe("Props passing to WorkflowsPanel", () => {
    it("passes selectedFlow prop correctly", () => {
      render(
        <AgentFlowGraph
          selectedFlow={mockFlow}
          setSelectedFlow={vi.fn()}
        />,
      );

      expect(workflowsPanelSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          selectedFlow: mockFlow,
        }),
      );
    });

    it("passes onFlowSelect callback (via handleFlowSelect)", () => {
      render(
        <AgentFlowGraph
          selectedFlow={null}
          setSelectedFlow={vi.fn()}
        />,
      );

      expect(workflowsPanelSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          onFlowSelect: expect.any(Function),
        }),
      );
    });

    it("passes onFlowDelete callback (via handleFlowDelete)", () => {
      render(
        <AgentFlowGraph
          selectedFlow={null}
          setSelectedFlow={vi.fn()}
        />,
      );

      expect(workflowsPanelSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          onFlowDelete: expect.any(Function),
        }),
      );
    });

    it("passes onValidationChange callback correctly", () => {
      const onValidationChange = vi.fn();
      render(
        <AgentFlowGraph
          selectedFlow={null}
          setSelectedFlow={vi.fn()}
          onValidationChange={onValidationChange}
        />,
      );

      expect(workflowsPanelSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          onValidationChange,
        }),
      );
    });

    it("sets showActiveStatus={true}", () => {
      render(
        <AgentFlowGraph
          selectedFlow={null}
          setSelectedFlow={vi.fn()}
        />,
      );

      expect(workflowsPanelSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          showActiveStatus: true,
        }),
      );
    });

    it("sets showDeleteButton={true}", () => {
      render(
        <AgentFlowGraph
          selectedFlow={null}
          setSelectedFlow={vi.fn()}
        />,
      );

      expect(workflowsPanelSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          showDeleteButton: true,
        }),
      );
    });

    it("sets useResolvedEndpoint={true}", () => {
      render(
        <AgentFlowGraph
          selectedFlow={null}
          setSelectedFlow={vi.fn()}
        />,
      );

      expect(workflowsPanelSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          useResolvedEndpoint: true,
        }),
      );
    });

    it("sets height='100%'", () => {
      render(
        <AgentFlowGraph
          selectedFlow={null}
          setSelectedFlow={vi.fn()}
        />,
      );

      expect(workflowsPanelSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          height: "100%",
        }),
      );
    });

    it("passes graphProps with correct values", () => {
      render(
        <AgentFlowGraph
          selectedFlow={null}
          setSelectedFlow={vi.fn()}
        />,
      );

      expect(workflowsPanelSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          graphProps: {
            showControls: true,
            showMiniMap: false,
            showBackground: true,
            interactive: true,
            isLiveRequest: false,
          },
        }),
      );
    });
  });

  describe("Flow selection behavior", () => {
    it("calls setSelectedFlow(flow) when flow is selected", async () => {
      const user = userEvent.setup();
      const setSelectedFlow = vi.fn();

      render(
        <AgentFlowGraph
          selectedFlow={null}
          setSelectedFlow={setSelectedFlow}
        />,
      );

      await user.click(screen.getByRole("button", { name: "Select Flow" }));
      expect(setSelectedFlow).toHaveBeenCalledWith(mockFlow);
    });

    it("passes null when clearing selection", async () => {
      const user = userEvent.setup();
      const setSelectedFlow = vi.fn();

      render(
        <AgentFlowGraph
          selectedFlow={mockFlow}
          setSelectedFlow={setSelectedFlow}
        />,
      );

      await user.click(screen.getByRole("button", { name: "Clear Selection" }));
      expect(setSelectedFlow).toHaveBeenCalledWith(null);
    });
  });

  describe("Flow deletion behavior", () => {
    it("clears selection (setSelectedFlow(null)) when deleted flow matches selected flow", async () => {
      const user = userEvent.setup();
      const setSelectedFlow = vi.fn();

      render(
        <AgentFlowGraph
          selectedFlow={mockFlow}
          setSelectedFlow={setSelectedFlow}
        />,
      );

      await user.click(screen.getByRole("button", { name: "Delete Selected Flow" }));
      expect(setSelectedFlow).toHaveBeenCalledWith(null);
    });

    it("does nothing when deleted flow is different from selected flow", async () => {
      const user = userEvent.setup();
      const setSelectedFlow = vi.fn();

      render(
        <AgentFlowGraph
          selectedFlow={mockFlow}
          setSelectedFlow={setSelectedFlow}
        />,
      );

      await user.click(screen.getByRole("button", { name: "Delete Different Flow" }));
      expect(setSelectedFlow).not.toHaveBeenCalled();
    });
  });

  describe("Validation callback", () => {
    it("triggers onValidationChange with error when validation fails", async () => {
      const user = userEvent.setup();
      const onValidationChange = vi.fn();

      render(
        <AgentFlowGraph
          selectedFlow={mockFlow}
          setSelectedFlow={vi.fn()}
          onValidationChange={onValidationChange}
        />,
      );

      await user.click(
        screen.getByRole("button", { name: "Trigger Validation Error" }),
      );
      expect(onValidationChange).toHaveBeenCalledWith(
        false,
        { errors: ["invalid"] },
        false,
      );
    });

    it("triggers onValidationChange with success when validation passes", async () => {
      const user = userEvent.setup();
      const onValidationChange = vi.fn();

      render(
        <AgentFlowGraph
          selectedFlow={mockFlow}
          setSelectedFlow={vi.fn()}
          onValidationChange={onValidationChange}
        />,
      );

      await user.click(
        screen.getByRole("button", { name: "Trigger Validation Success" }),
      );
      expect(onValidationChange).toHaveBeenCalledWith(true, null, false);
    });
  });

  describe("Graph data handling", () => {
    it("renders header and graph canvas details from props", () => {
      render(
        <AgentFlowGraph
          selectedFlow={mockFlow}
          setSelectedFlow={vi.fn()}
        />,
      );

      expect(
        screen.getByText("Agent Workflow Visualization"),
      ).toBeInTheDocument();
      expect(screen.getByTestId("graph-canvas")).toHaveTextContent(
        "Nodes: 0 Edges: 0",
      );
    });

    it("handles empty graph data gracefully", () => {
      render(
        <AgentFlowGraph
          selectedFlow={{
            ...mockFlow,
            flow: { nodes: [], edges: [] },
          }}
          setSelectedFlow={vi.fn()}
        />,
      );

      expect(screen.getByTestId("graph-canvas")).toHaveTextContent(
        "Nodes: 0 Edges: 0",
      );
    });
  });
});
