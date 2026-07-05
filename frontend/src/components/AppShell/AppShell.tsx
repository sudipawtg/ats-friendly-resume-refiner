"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Download,
  FileText,
  FlaskConical,
  Inbox,
  Layers,
  LayoutDashboard,
  Menu,
  PenLine,
  Search,
  Settings2,
  Sparkles,
  X,
} from "lucide-react";
import clsx from "clsx";
import { useCallback, useState } from "react";
import { Logo } from "@/components/Logo";
import { NAV_GROUPS, NAV_ITEMS } from "@/constants";

const ICON_MAP = {
  LayoutDashboard,
  FlaskConical,
  FileText,
  PenLine,
  Search,
  Inbox,
  Sparkles,
  Layers,
  Settings2,
  Download,
} as const;

interface AppShellProps {
  children: React.ReactNode;
}

function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const groups = Object.keys(NAV_GROUPS) as Array<keyof typeof NAV_GROUPS>;

  return (
    <nav className="flex-1 space-y-4 px-3 py-4">
      {groups.map((groupKey) => {
        const items = NAV_ITEMS.filter((item) => item.group === groupKey);
        if (items.length === 0) return null;
        return (
          <div key={groupKey}>
            <p className="mb-1.5 px-3 text-apple-caption font-semibold uppercase tracking-wider text-apple-label-tertiary">
              {NAV_GROUPS[groupKey]}
            </p>
            <div className="space-y-0.5">
              {items.map((item) => {
                const Icon = ICON_MAP[item.icon as keyof typeof ICON_MAP];
                const isActive =
                  pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={onNavigate}
                    className={clsx(isActive ? "nav-item-active" : "nav-item")}
                    data-testid={`nav-${item.href.replace("/", "") || "dashboard"}`}
                  >
                    <Icon size={18} strokeWidth={isActive ? 2.25 : 2} />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        );
      })}
    </nav>
  );
}

export function AppShell({ children }: AppShellProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleCloseMobile = useCallback(() => {
    setMobileOpen(false);
  }, []);

  const handleOpenMobile = useCallback(() => {
    setMobileOpen(true);
  }, []);

  return (
    <div className="flex min-h-screen">
      <aside
        className="fixed left-0 top-0 z-40 hidden h-screen w-sidebar flex-col border-r border-apple-separator/60 bg-apple-sidebar shadow-apple backdrop-blur-2xl backdrop-saturate-150 md:flex"
        data-testid="app-sidebar"
      >
        <div className="border-b border-apple-separator/50 px-5 py-5">
          <Link href="/" className="block transition-opacity hover:opacity-90">
            <Logo size="md" />
          </Link>
        </div>
        <SidebarNav />
      </aside>

      {mobileOpen ? (
        <div className="fixed inset-0 z-50 md:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-slate-900/25 backdrop-blur-sm"
            onClick={handleCloseMobile}
            aria-label="Close menu"
          />
          <aside className="absolute left-0 top-0 flex h-full w-[min(280px,85vw)] flex-col bg-apple-sidebar shadow-apple-lg backdrop-blur-2xl">
            <div className="flex items-center justify-between border-b border-apple-separator/50 px-5 py-4">
              <Link href="/" onClick={handleCloseMobile} className="transition-opacity hover:opacity-90">
                <Logo size="sm" />
              </Link>
              <button type="button" onClick={handleCloseMobile} className="glass-button p-2" aria-label="Close">
                <X size={18} />
              </button>
            </div>
            <SidebarNav onNavigate={handleCloseMobile} />
          </aside>
        </div>
      ) : null}

      <div className="flex min-h-screen flex-1 flex-col md:ml-sidebar">
        <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-apple-separator/50 bg-apple-bg/85 px-4 py-3 backdrop-blur-xl md:hidden">
          <button type="button" onClick={handleOpenMobile} className="glass-button p-2" aria-label="Open menu">
            <Menu size={20} />
          </button>
          <Link href="/" className="transition-opacity hover:opacity-90">
            <Logo size="sm" showWordmark={false} />
          </Link>
        </header>

        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-10 lg:py-8">
          <div className="mx-auto max-w-[1200px]">{children}</div>
        </main>
      </div>
    </div>
  );
}
