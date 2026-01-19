import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WorkflowList } from "../WorkflowList";
import { render } from "@/test-utils/render";

describe("WorkflowList", () => {
  it("renders empty state when no workflows", () => {
    render(
      <WorkflowList
        title="Workflows"
        workflows={[]}
        isLoading={false}
        onWorkflowClick={vi.fn()}
        emptyMessage="No workflows"
      />,
    );

    expect(screen.getByText("No workflows")).toBeInTheDocument();
  });

  it("invokes onWorkflowClick when a card is clicked", async () => {
    const user = userEvent.setup();
    const onWorkflowClick = vi.fn();

    render(
      <WorkflowList
        title="Workflows"
        workflows={[{ blueprint_id: "bp-1", spec_dict: { name: "Flow A" } }]}
        isLoading={false}
        onWorkflowClick={onWorkflowClick}
        emptyMessage="No workflows"
      />,
    );

    await user.click(screen.getByRole("button", { name: "Workflow: Flow A" }));
    expect(onWorkflowClick).toHaveBeenCalledTimes(1);
  });
});

