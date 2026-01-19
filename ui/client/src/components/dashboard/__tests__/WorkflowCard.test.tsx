import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WorkflowCard } from "../WorkflowCard";
import { render } from "@/test-utils/render";

describe("WorkflowCard", () => {
  it("handles click and keyboard activation", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();

    render(
      <WorkflowCard
        workflow={{ blueprint_id: "bp-1", spec_dict: { name: "Workflow A" } }}
        index={0}
        onClick={onClick}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Workflow: Workflow A" }));
    expect(onClick).toHaveBeenCalledTimes(1);

    await user.keyboard("{Enter}");
    expect(onClick).toHaveBeenCalledTimes(2);
  });
});

