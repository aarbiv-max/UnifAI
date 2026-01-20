import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StreamingDataProvider, useStreamingData } from "../StreamingDataContext";
import { render } from "@/test-utils/render";

const TestConsumer = () => {
  const { nodeListRef, forceUpdate, clearStream } = useStreamingData();

  return (
    <div>
      <span data-testid="count">{nodeListRef.current.size}</span>
      <button
        type="button"
        onClick={() => {
          nodeListRef.current.set("node-1", { id: "node-1" } as any);
          forceUpdate();
        }}
      >
        Add
      </button>
      <button type="button" onClick={clearStream}>
        Clear
      </button>
    </div>
  );
};

describe("StreamingDataContext", () => {
  it("initializes with defaults and updates on changes", async () => {
    const user = userEvent.setup();

    render(
      <StreamingDataProvider>
        <TestConsumer />
      </StreamingDataProvider>,
    );

    expect(screen.getByTestId("count")).toHaveTextContent("0");

    await user.click(screen.getByRole("button", { name: "Add" }));
    expect(screen.getByTestId("count")).toHaveTextContent("1");

    await user.click(screen.getByRole("button", { name: "Clear" }));
    expect(screen.getByTestId("count")).toHaveTextContent("0");
  });

  it("throws when used outside the provider", () => {
    const ConsumerOutside = () => {
      useStreamingData();
      return <div>Outside</div>;
    };

    expect(() => render(<ConsumerOutside />)).toThrow(
      "useStreamingData must be used within a StreamingDataProvider",
    );
  });
});


