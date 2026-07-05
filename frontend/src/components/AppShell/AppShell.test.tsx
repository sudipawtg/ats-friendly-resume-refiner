import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { AppShell } from "./AppShell";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    className,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    className?: string;
  }) => (
    <a href={href} className={className} {...props}>
      {children}
    </a>
  ),
}));

const mockPathname = vi.fn(() => "/");

vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname(),
}));

describe("AppShell", () => {
  it("renders sidebar with data-testid", () => {
    render(
      <AppShell>
        <div data-testid="page-content">Page</div>
      </AppShell>
    );
    expect(screen.getByTestId("app-sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("page-content")).toHaveTextContent("Page");
  });

  it("renders all navigation links", () => {
    render(
      <AppShell>
        <span>Child</span>
      </AppShell>
    );
    expect(screen.getByTestId("nav-dashboard")).toBeInTheDocument();
    expect(screen.getByTestId("nav-cvs")).toBeInTheDocument();
    expect(screen.getByTestId("nav-edit")).toBeInTheDocument();
    expect(screen.getByTestId("nav-discover")).toBeInTheDocument();
    expect(screen.getByTestId("nav-jobs")).toBeInTheDocument();
    expect(screen.getByTestId("nav-batch")).toBeInTheDocument();
    expect(screen.getByTestId("nav-instructions")).toBeInTheDocument();
    expect(screen.getByTestId("nav-outputs")).toBeInTheDocument();
  });

  it("shows ResumeForge branding", () => {
    render(
      <AppShell>
        <span>Child</span>
      </AppShell>
    );
    expect(screen.getAllByTestId("logo-mark").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Resume").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Forge").length).toBeGreaterThan(0);
  });

  it("highlights active nav item for current path", () => {
    mockPathname.mockReturnValue("/cvs");
    render(
      <AppShell>
        <span>Child</span>
      </AppShell>
    );
    const cvsLink = screen.getByTestId("nav-cvs");
    expect(cvsLink.className).toContain("nav-item-active");
  });

  it("highlights dashboard for root path", () => {
    mockPathname.mockReturnValue("/");
    render(
      <AppShell>
        <span>Child</span>
      </AppShell>
    );
    const dashboardLink = screen.getByTestId("nav-dashboard");
    expect(dashboardLink.className).toContain("nav-item-active");
  });
});
