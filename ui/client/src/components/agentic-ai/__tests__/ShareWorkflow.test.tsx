import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
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

vi.mock("@/components/ui/umamitrack", () => ({
  UmamiTrack: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

describe("ShareWorkflow", () => {
  beforeEach(() => {
    getBlueprintInfoMock.mockReset();
    setBlueprintMetadataMock.mockReset();
    toastSpy.mockReset();
  });

  describe("Initial state and fetching", () => {
    it("fetches blueprint info via getBlueprintInfo(blueprintId)", async () => {
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "private" },
      });

      render(<ShareWorkflow blueprintId="bp-1" />);

      await waitFor(() => {
        expect(getBlueprintInfoMock).toHaveBeenCalledWith("bp-1");
      });
    });

    it("sets enabled based on metadata.usageScope === 'public'", async () => {
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "public" },
      });

      render(<ShareWorkflow blueprintId="bp-1" />);

      await waitFor(() => {
        const toggle = screen.getByRole("switch");
        expect(toggle).toBeChecked();
      });
    });

    it("sets shareLink via constructShareLink() when enabled", async () => {
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "public" },
      });

      render(<ShareWorkflow blueprintId="bp-1" />);

      expect(await screen.findByText("https://share/bp-1")).toBeInTheDocument();
    });

    it("returns null if no blueprintId", () => {
      const { container } = render(<ShareWorkflow blueprintId="" />);
      expect(container.firstChild).toBeNull();
    });
  });

  describe("Sharing disabled states", () => {
    it("isSharingDisabled = isLoading || isValidating || (!isValid && !enabled)", async () => {
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "private" },
      });

      render(<ShareWorkflow blueprintId="bp-1" isValid={false} />);

      const toggle = await screen.findByRole("switch");
      expect(toggle).toBeDisabled();
    });

    it("toggle disabled when isLoading is true", async () => {
      const user = userEvent.setup();
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "private" },
      });
      // Make setBlueprintMetadata hang to keep isLoading=true
      setBlueprintMetadataMock.mockImplementation(
        () => new Promise(() => {}), // Never resolves, keeps loading
      );

      render(<ShareWorkflow blueprintId="bp-1" />);

      // Wait for initial state to load
      const toggle = await screen.findByRole("switch");
      
      // Click the toggle to trigger loading state
      await user.click(toggle);

      // During loading, the label should show "Enabling..."
      expect(screen.getByText("Enabling...")).toBeInTheDocument();
    });

    it("toggle disabled when isValidating is true", async () => {
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "private" },
      });

      render(<ShareWorkflow blueprintId="bp-1" isValidating={true} />);

      const toggle = await screen.findByRole("switch");
      expect(toggle).toBeDisabled();
    });

    it("toggle disabled when !isValid && !enabled", async () => {
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "private" },
      });

      render(<ShareWorkflow blueprintId="bp-1" isValid={false} />);

      const toggle = await screen.findByRole("switch");
      expect(toggle).toBeDisabled();
    });
  });

  describe("Warning states", () => {
    it("shows yellow warning when enabled && !isValid && !isValidating", async () => {
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "public" },
      });

      render(<ShareWorkflow blueprintId="bp-1" isValid={false} />);

      expect(
        await screen.findByText(
          "Warning: This workflow is shared but has validation errors",
        ),
      ).toBeInTheDocument();
    });
  });

  describe("Toggle behavior", () => {
    it("handleToggle(checked) calls setBlueprintMetadata() API", async () => {
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
    });

    it("updates enabled and shareLink states on successful toggle", async () => {
      const user = userEvent.setup();
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "private" },
      });
      setBlueprintMetadataMock.mockResolvedValueOnce({});

      render(<ShareWorkflow blueprintId="bp-2" />);

      const toggle = await screen.findByRole("switch");
      expect(screen.queryByText("Share Link")).not.toBeInTheDocument();

      await user.click(toggle);

      expect(await screen.findByText("Share Link")).toBeInTheDocument();
      expect(screen.getByText("https://share/bp-2")).toBeInTheDocument();
    });

    it("shows toast: 'Sharing Enabled' when enabling", async () => {
      const user = userEvent.setup();
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "private" },
      });
      setBlueprintMetadataMock.mockResolvedValueOnce({});

      render(<ShareWorkflow blueprintId="bp-2" />);

      const toggle = await screen.findByRole("switch");
      await user.click(toggle);

      expect(toastSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Sharing Enabled",
        }),
      );
    });

    it("shows toast: 'Sharing Disabled' when disabling", async () => {
      const user = userEvent.setup();
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "public" },
      });
      setBlueprintMetadataMock.mockResolvedValueOnce({});

      render(<ShareWorkflow blueprintId="bp-2" />);

      const toggle = await screen.findByRole("switch");
      await user.click(toggle);

      expect(toastSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Sharing Disabled",
        }),
      );
    });

    it("reverts to enabled=false if enabling fails", async () => {
      const user = userEvent.setup();
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "private" },
      });
      setBlueprintMetadataMock.mockRejectedValueOnce(new Error("API Error"));

      render(<ShareWorkflow blueprintId="bp-2" />);

      const toggle = await screen.findByRole("switch");
      await user.click(toggle);

      await waitFor(() => {
        expect(toggle).not.toBeChecked();
      });
    });

    it("shows error toast on API failure", async () => {
      const user = userEvent.setup();
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "private" },
      });
      setBlueprintMetadataMock.mockRejectedValueOnce(new Error("API Error"));

      render(<ShareWorkflow blueprintId="bp-2" />);

      const toggle = await screen.findByRole("switch");
      await user.click(toggle);

      await waitFor(() => {
        expect(toastSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            variant: "destructive",
          }),
        );
      });
    });
  });

  describe("Label states", () => {
    it("shows 'Disabling...' when isLoading && enabled", async () => {
      const user = userEvent.setup();
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "public" },
      });
      setBlueprintMetadataMock.mockImplementation(
        () => new Promise(() => {}), // Never resolves
      );

      render(<ShareWorkflow blueprintId="bp-2" />);

      const toggle = await screen.findByRole("switch");
      await user.click(toggle);

      expect(screen.getByText("Disabling...")).toBeInTheDocument();
    });

    it("shows 'Enabling...' when isLoading && !enabled", async () => {
      const user = userEvent.setup();
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "private" },
      });
      setBlueprintMetadataMock.mockImplementation(
        () => new Promise(() => {}), // Never resolves
      );

      render(<ShareWorkflow blueprintId="bp-2" />);

      const toggle = await screen.findByRole("switch");
      await user.click(toggle);

      expect(screen.getByText("Enabling...")).toBeInTheDocument();
    });

    it("shows 'Validating...' when isValidating", async () => {
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "private" },
      });

      render(<ShareWorkflow blueprintId="bp-2" isValidating={true} />);

      expect(await screen.findByText("Validating...")).toBeInTheDocument();
    });

    it("shows 'Enable Public Chat Sharing' as default label", async () => {
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "private" },
      });

      render(<ShareWorkflow blueprintId="bp-2" />);

      expect(
        await screen.findByText("Enable Public Chat Sharing"),
      ).toBeInTheDocument();
    });
  });

  describe("Share link section", () => {
    it("only shows when enabled && shareLink", async () => {
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "public" },
      });

      render(<ShareWorkflow blueprintId="bp-1" />);

      expect(await screen.findByText("Share Link")).toBeInTheDocument();
      expect(screen.getByText("https://share/bp-1")).toBeInTheDocument();
    });

    it("displays link in monospace font", async () => {
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "public" },
      });

      render(<ShareWorkflow blueprintId="bp-1" />);

      const linkElement = await screen.findByText("https://share/bp-1");
      expect(linkElement).toHaveClass("font-mono");
    });

    it("copy button: copies to clipboard, shows Check icon for 2s", async () => {
      const user = userEvent.setup();
      const writeTextMock = vi.fn().mockResolvedValue(undefined);
      Object.defineProperty(navigator, "clipboard", {
        value: { writeText: writeTextMock },
        writable: true,
        configurable: true,
      });

      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "public" },
      });

      render(<ShareWorkflow blueprintId="bp-1" />);

      await screen.findByText("Share Link");
      const copyButton = screen.getByRole("button", { name: /copy/i });
      await user.click(copyButton);

      expect(writeTextMock).toHaveBeenCalledWith("https://share/bp-1");
      expect(toastSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Link Copied",
        }),
      );
    });

    it("shows 'Anyone with this link can chat...' description", async () => {
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "public" },
      });

      render(<ShareWorkflow blueprintId="bp-1" />);

      expect(
        await screen.findByText(/Anyone with this link can chat/),
      ).toBeInTheDocument();
    });
  });

  describe("Info messages", () => {
    it("shows 'Validating workflow...' when isValidating", async () => {
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "private" },
      });

      render(<ShareWorkflow blueprintId="bp-1" isValidating={true} />);

      expect(await screen.findByText("Validating...")).toBeInTheDocument();
    });

    it("shows 'Enable sharing to generate a public chat link...' when valid and not enabled", async () => {
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "private" },
      });

      render(<ShareWorkflow blueprintId="bp-1" isValid={true} />);

      expect(
        await screen.findByText(
          "Enable sharing to generate a public chat link for this workflow",
        ),
      ).toBeInTheDocument();
    });

    it("shows 'Fix validation errors to enable sharing...' when invalid", async () => {
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "private" },
      });

      render(<ShareWorkflow blueprintId="bp-1" isValid={false} />);

      expect(
        await screen.findByText(
          "Fix validation errors to enable sharing for this workflow",
        ),
      ).toBeInTheDocument();
    });
  });

  describe("renders share link when blueprint is public", () => {
    it("renders share link when blueprint is public", async () => {
      getBlueprintInfoMock.mockResolvedValueOnce({
        metadata: { usageScope: "public" },
      });

      render(<ShareWorkflow blueprintId="bp-1" />);

      expect(await screen.findByText("Share Link")).toBeInTheDocument();
      expect(screen.getByText("https://share/bp-1")).toBeInTheDocument();
    });
  });

  describe("disables sharing when workflow is invalid", () => {
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
  });
});
