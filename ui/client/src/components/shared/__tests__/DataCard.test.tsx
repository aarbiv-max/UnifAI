import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DataCard } from "../DataCard";
import { render } from "@/test-utils/render";
import { PIPELINE_STATUS } from "@/constants/pipelineStatus";

describe("DataCard", () => {
  it("renders title, subtitle, status, and metadata", () => {
    render(
      <DataCard
        title="Demo card"
        subtitle="Subtitle"
        status={PIPELINE_STATUS.DONE}
        metadata="Metadata"
        footer="Footer"
      />,
    );

    expect(screen.getByText("Demo card")).toBeInTheDocument();
    expect(screen.getByText("Subtitle")).toBeInTheDocument();
    expect(screen.getByText("Done")).toBeInTheDocument();
    expect(screen.getByText("Metadata")).toBeInTheDocument();
    expect(screen.getByText("Footer")).toBeInTheDocument();
  });

  it("opens confirm dialog for action with confirmation", async () => {
    const user = userEvent.setup();
    const confirmHandler = vi.fn().mockResolvedValue(undefined);

    render(
      <DataCard
        title="Card"
        actions={[
          {
            icon: <span>!</span>,
            onClick: vi.fn(),
            confirm: {
              title: "Confirm action",
              message: "Are you sure?",
              onConfirm: confirmHandler,
            },
          },
        ]}
      />,
    );

    await user.click(screen.getByRole("button"));
    expect(screen.getByText("Confirm action")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Confirm" }));
    expect(confirmHandler).toHaveBeenCalledTimes(1);
  });
});

