import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@/test-utils/render";
import type { FlowObject } from "../graphs/interfaces";
import WorkflowsPanel from "../WorkflowsPanel";

const flow: FlowObject = {
  id: "bp-1",
  name: "Flow One",
  description: "Flow description",
  icon: <span>Icon</span>,
  flow: { nodes: [], edges: [] },
};

const fetchBlueprintsMock = vi.fn();
const fetchResolvedBlueprintsMock = vi.fn();
const fetchActiveSessionsMock = vi.fn();
const deleteBlueprintMock = vi.fn();

const authState = {
  user: { username: "tester" },
  isAuthenticated: true,
  isLoading: false,
  login: vi.fn(),
  logout: vi.fn(),
  checkAuthStatus: vi.fn(),
};

vi.mock("@/contexts/AuthContext", () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth: () => authState,
}));

const openShareForItemMock = vi.fn();
vi.mock("@/contexts/SharedContext", () => ({
  SharedProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useShared: () => ({ openShareForItem: openShareForItemMock }),
}));

vi.mock("@/api/agentic", () => ({
  fetchActiveSessions: (...args: any[]) => fetchActiveSessionsMock(...args),
}));

vi.mock("@/api/blueprints", () => ({
  fetchBlueprints: (...args: any[]) => fetchBlueprintsMock(...args),
  fetchResolvedBlueprints: (...args: any[]) =>
    fetchResolvedBlueprintsMock(...args),
  deleteBlueprint: (...args: any[]) => deleteBlueprintMock(...args),
}));

vi.mock("@/utils/blueprintHelpers", () => ({
  convertGraphFlowToFlowObject: () => flow,
}));

const validationState = {
  isValidating: false,
  validationResults: null,
  isValid: true,
};

vi.mock("@/hooks/use-blueprint-validation", () => ({
  useBlueprintValidation: () => ({
    ...validationState,
    validateBlueprint: vi.fn(),
    clearValidation: vi.fn(),
  }),
}));

vi.mock("../graphs/ReactFlowGraph", () => ({
  default: () => <div>ReactFlowGraph</div>,
}));

vi.mock("../ShareWorkflow", () => ({
  default: () => <div>ShareWorkflow</div>,
}));

describe("WorkflowsPanel", () => {
  beforeEach(() => {
    fetchBlueprintsMock.mockReset();
    fetchResolvedBlueprintsMock.mockReset();
    fetchActiveSessionsMock.mockReset();
    deleteBlueprintMock.mockReset();
    openShareForItemMock.mockReset();
    fetchBlueprintsMock.mockResolvedValue([]);
    fetchResolvedBlueprintsMock.mockResolvedValue([]);
    fetchActiveSessionsMock.mockResolvedValue([]);
    deleteBlueprintMock.mockResolvedValue({});
  });

  it("renders flows and auto-selects the first flow", async () => {
    fetchBlueprintsMock.mockResolvedValueOnce([
      { blueprint_id: "bp-1", spec_dict: { name: "Flow One" } },
    ]);
    fetchActiveSessionsMock.mockResolvedValueOnce([]);
    const onFlowSelect = vi.fn();

    render(
      <WorkflowsPanel
        selectedFlow={null}
        onFlowSelect={onFlowSelect}
      />,
    );

    expect(await screen.findByText("Flow One")).toBeInTheDocument();
    await waitFor(() => {
      expect(onFlowSelect).toHaveBeenCalledWith(flow);
    });
  });

  it("shows empty state when no workflows are available", async () => {
    fetchBlueprintsMock.mockResolvedValueOnce([]);
    fetchActiveSessionsMock.mockResolvedValueOnce([]);

    render(
      <WorkflowsPanel
        selectedFlow={null}
        onFlowSelect={vi.fn()}
      />,
    );

    expect(await screen.findByText("No flows available")).toBeInTheDocument();
  });

  it("selects a workflow when clicked", async () => {
    fetchBlueprintsMock.mockResolvedValueOnce([
      { blueprint_id: "bp-1", spec_dict: { name: "Flow One" } },
    ]);
    fetchActiveSessionsMock.mockResolvedValueOnce([]);
    const onFlowSelect = vi.fn();

    render(
      <WorkflowsPanel
        selectedFlow={null}
        onFlowSelect={onFlowSelect}
      />,
    );

    const label = await screen.findByText("Flow One");
    const user = userEvent.setup();
    await user.click(label);
    expect(onFlowSelect).toHaveBeenCalledWith(flow);
  });

  it("opens share for a flow", async () => {
    fetchBlueprintsMock.mockResolvedValueOnce([
      { blueprint_id: "bp-1", spec_dict: { name: "Flow One" } },
    ]);
    fetchActiveSessionsMock.mockResolvedValueOnce([]);

    render(
      <WorkflowsPanel
        selectedFlow={flow}
        onFlowSelect={vi.fn()}
      />,
    );

    const user = userEvent.setup();
    const flowLabel = await screen.findByText("Flow One");
    let flowRow: HTMLElement | null = flowLabel;
    while (flowRow && flowRow.querySelectorAll("button").length === 0) {
      flowRow = flowRow.parentElement;
    }
    if (!flowRow) {
      throw new Error("Flow row not found for share action");
    }
    const shareButton = flowRow.querySelector("button");
    if (!shareButton) {
      throw new Error("Share button not found for flow row");
    }
    await user.click(shareButton);
    expect(openShareForItemMock).toHaveBeenCalledWith({
      itemKind: "blueprint",
      itemId: "bp-1",
      itemName: "Flow One",
    });
  });

  it("deletes a flow via confirmation dialog", async () => {
    fetchBlueprintsMock.mockResolvedValueOnce([
      { blueprint_id: "bp-1", spec_dict: { name: "Flow One" } },
    ]);
    fetchActiveSessionsMock.mockResolvedValueOnce([]);
    deleteBlueprintMock.mockResolvedValueOnce({});
    const onFlowDelete = vi.fn();

    render(
      <WorkflowsPanel
        selectedFlow={flow}
        onFlowSelect={vi.fn()}
        onFlowDelete={onFlowDelete}
        showDeleteButton
      />,
    );

    const user = userEvent.setup();
    const flowLabel = await screen.findByText("Flow One");
    let flowRow: HTMLElement | null = flowLabel;
    while (flowRow && flowRow.querySelectorAll("button").length < 2) {
      flowRow = flowRow.parentElement;
    }
    if (!flowRow) {
      throw new Error("Flow row not found for delete action");
    }
    const rowButtons = flowRow.querySelectorAll("button");
    const deleteButton = rowButtons[rowButtons.length - 1];
    await user.click(deleteButton);

    const confirmButton = await screen.findByRole("button", { name: "Confirm" });
    await user.click(confirmButton);
    expect(deleteBlueprintMock).toHaveBeenCalledWith("bp-1");
    expect(onFlowDelete).toHaveBeenCalledWith(flow);
  });
});

