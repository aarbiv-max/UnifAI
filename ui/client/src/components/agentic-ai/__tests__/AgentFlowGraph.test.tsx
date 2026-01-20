import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
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

const workflowsPanelSpy = vi.fn();

vi.mock("../WorkflowsPanel", () => ({
  default: (props: any) => {
    workflowsPanelSpy(props);
    const nodeCount = props.selectedFlow?.flow?.nodes?.length ?? 0;
    const edgeCount = props.selectedFlow?.flow?.edges?.length ?? 0;

    return (
      <div>
        <div data-testid="graph-canvas">
          Nodes: {nodeCount} Edges: {edgeCount}
        </div>
        <button type="button" onClick={() => props.onFlowSelect?.(mockFlow)}>
          Select Flow
        </button>
        <button type="button" onClick={() => props.onFlowDelete?.(mockFlow)}>
          Delete Flow
        </button>
        <button
          type="button"
          onClick={() =>
            props.onValidationChange?.(false, { errors: ["invalid"] }, false)
          }
        >
          Trigger Validation Error
        </button>
      </div>
    );
  },
}));

import AgentFlowGraph from "../AgentFlowGraph";

describe("AgentFlowGraph", () => {
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

  it("selects a flow and triggers validation callback", async () => {
    const user = userEvent.setup();
    const setSelectedFlow = vi.fn();
    const onValidationChange = vi.fn();

    render(
      <AgentFlowGraph
        selectedFlow={null}
        setSelectedFlow={setSelectedFlow}
        onValidationChange={onValidationChange}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Select Flow" }));
    expect(setSelectedFlow).toHaveBeenCalledWith(mockFlow);

    await user.click(
      screen.getByRole("button", { name: "Trigger Validation Error" }),
    );
    expect(onValidationChange).toHaveBeenCalledWith(
      false,
      { errors: ["invalid"] },
      false,
    );
  });

  it("clears selection when deleting selected flow", async () => {
    const user = userEvent.setup();
    const setSelectedFlow = vi.fn();

    render(
      <AgentFlowGraph
        selectedFlow={mockFlow}
        setSelectedFlow={setSelectedFlow}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Delete Flow" }));
    expect(setSelectedFlow).toHaveBeenCalledWith(null);
  });

  it("passes zoom/fit controls props to the workflows panel", () => {
    render(
      <AgentFlowGraph
        selectedFlow={mockFlow}
        setSelectedFlow={vi.fn()}
      />,
    );

    expect(workflowsPanelSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        graphProps: expect.objectContaining({
          showControls: true,
          showBackground: true,
          showMiniMap: false,
        }),
        showActiveStatus: true,
        showDeleteButton: true,
        useResolvedEndpoint: true,
      }),
    );
  });
});


