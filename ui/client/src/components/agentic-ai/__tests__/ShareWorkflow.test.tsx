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

  it("enables sharing when toggled", async () => {
    const user = userEvent.setup();
    getBlueprintInfoMock.mockResolvedValueOnce({
      metadata: { usageScope: "private" },
    });
    setBlueprintMetadataMock.mockResolvedValueOnce({});

    render(<ShareWorkflow blueprintId="bp-2" />);

    const toggle = await screen.findByRole("switch");
    await user.click(toggle);

    expect(setBlueprintMetadataMock).toHaveBeenCalledWith(
      "bp-2",
      { usageScope: "public" },
      "tester",
    );
    expect(toastSpy).toHaveBeenCalled();
  });
});

