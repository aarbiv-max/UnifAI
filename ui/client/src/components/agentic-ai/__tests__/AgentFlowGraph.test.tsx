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

vi.mock("../WorkflowsPanel", () => ({
  default: (props: any) => (
    <div>
      <button type="button" onClick={() => props.onFlowSelect?.(mockFlow)}>
        Select Flow
      </button>
      <button type="button" onClick={() => props.onFlowDelete?.(mockFlow)}>
        Delete Flow
      </button>
    </div>
  ),
}));

import AgentFlowGraph from "../AgentFlowGraph";

describe("AgentFlowGraph", () => {
  it("renders header and selects a flow", async () => {
    const user = userEvent.setup();
    const setSelectedFlow = vi.fn();

    render(
      <AgentFlowGraph
        selectedFlow={null}
        setSelectedFlow={setSelectedFlow}
      />,
    );

    expect(
      screen.getByText("Agent Workflow Visualization"),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Select Flow" }));
    expect(setSelectedFlow).toHaveBeenCalledWith(mockFlow);
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
});

