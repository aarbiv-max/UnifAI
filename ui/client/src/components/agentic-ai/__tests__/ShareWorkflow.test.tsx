import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@/test-utils/render";
import ShareWorkflow from "../ShareWorkflow";

const toastSpy = vi.fn();

vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({ toast: toastSpy }),
}));

vi.mock("@/contexts/AuthContext", () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth: () => ({
    user: { username: "tester" },
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    checkAuthStatus: vi.fn(),
  }),
}));

const getBlueprintInfoMock = vi.fn();
const setBlueprintMetadataMock = vi.fn();

vi.mock("@/api/blueprints", () => ({
  getBlueprintInfo: (...args: any[]) => getBlueprintInfoMock(...args),
  setBlueprintMetadata: (...args: any[]) => setBlueprintMetadataMock(...args),
}));

vi.mock("@/utils/blueprintHelpers", () => ({
  constructShareLink: (id: string) => `https://share/${id}`,
}));

describe("ShareWorkflow", () => {
  beforeEach(() => {
    getBlueprintInfoMock.mockReset();
    setBlueprintMetadataMock.mockReset();
    toastSpy.mockReset();
  });

  it("renders share link when blueprint is public", async () => {
    getBlueprintInfoMock.mockResolvedValueOnce({
      metadata: { usageScope: "public" },
    });

    render(<ShareWorkflow blueprintId="bp-1" />);

    expect(await screen.findByText("Share Link")).toBeInTheDocument();
    expect(screen.getByText("https://share/bp-1")).toBeInTheDocument();
  });

  it("toggles share panel open/close and shows success toast", async () => {
    const user = userEvent.setup();
    getBlueprintInfoMock.mockResolvedValueOnce({
      metadata: { usageScope: "private" },
    });
    setBlueprintMetadataMock.mockResolvedValueOnce({});
    setBlueprintMetadataMock.mockResolvedValueOnce({});

    render(<ShareWorkflow blueprintId="bp-2" />);

    const toggle = await screen.findByRole("switch");
    expect(screen.queryByText("Share Link")).not.toBeInTheDocument();

    await user.click(toggle);

    expect(setBlueprintMetadataMock).toHaveBeenCalledWith(
      "bp-2",
      { usageScope: "public" },
      "tester",
    );
    expect(toastSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "Sharing Enabled",
      }),
    );
    expect(await screen.findByText("Share Link")).toBeInTheDocument();

    await user.click(toggle);
    expect(setBlueprintMetadataMock).toHaveBeenCalledWith(
      "bp-2",
      { usageScope: "private" },
      "tester",
    );
    expect(screen.queryByText("Share Link")).not.toBeInTheDocument();
  });

  it("disables sharing when workflow is invalid", async () => {
    getBlueprintInfoMock.mockResolvedValueOnce({
      metadata: { usageScope: "private" },
    });

    render(<ShareWorkflow blueprintId="bp-3" isValid={false} />);

    const toggle = await screen.findByRole("switch");
    expect(toggle).toBeDisabled();
    expect(
      screen.getByText(
        "Fix validation errors to enable sharing for this workflow",
      ),
    ).toBeInTheDocument();
  });

  it("shows warning when sharing an invalid workflow", async () => {
    getBlueprintInfoMock.mockResolvedValueOnce({
      metadata: { usageScope: "public" },
    });

    render(<ShareWorkflow blueprintId="bp-4" isValid={false} />);

    expect(
      await screen.findByText(
        "Warning: This workflow is shared but has validation errors",
      ),
    ).toBeInTheDocument();
  });
});

