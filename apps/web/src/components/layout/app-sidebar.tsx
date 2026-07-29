"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { LayoutDashboard, Menu, X } from "lucide-react";
import { useMediaQuery, BREAKPOINTS } from "@/hooks/use-media-query";
import { SidebarContent } from "./sidebar-content";
import { cn } from "@/lib/utils";
import type { User } from "@supabase/supabase-js";

interface AppSidebarProps {
  user: User;
}

const mainNavItems = [
  { href: "/workspaces" as const, labelKey: "workspaces" as const, icon: LayoutDashboard },
];

export function AppSidebar({ user }: AppSidebarProps) {
  const t = useTranslations("common");
  const isDesktop = useMediaQuery(BREAKPOINTS.md);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  if (isDesktop) {
    return (
      <aside
        className={cn(
          "flex h-full shrink-0 flex-col border-r border-vault-border bg-vault-bg transition-[width] duration-200",
          collapsed ? "w-14" : "w-60",
        )}
      >
        <SidebarContent
          user={user}
          mainNavItems={mainNavItems}
          collapsed={collapsed}
          onToggleCollapse={() => setCollapsed((c) => !c)}
        />
      </aside>
    );
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setDrawerOpen(true)}
        className="fixed left-3 top-3 z-50 rounded border border-vault-border bg-vault-surface p-2 text-vault-text md:hidden"
        aria-label={t("menu")}
      >
        <Menu className="h-5 w-5" />
      </button>

      {drawerOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div
            className="absolute inset-0 bg-vault-bg/80 backdrop-blur-sm"
            onClick={() => setDrawerOpen(false)}
            aria-hidden="true"
          />
          <aside className="relative flex h-full w-70 max-w-[80vw] flex-col border-r border-vault-border bg-vault-bg animate-in slide-in-from-left duration-200">
            <button
              type="button"
              onClick={() => setDrawerOpen(false)}
              className="absolute right-2 top-3 rounded p-1 text-vault-text-muted hover:text-vault-text"
              aria-label={t("close")}
            >
              <X className="h-4 w-4" />
            </button>
            <SidebarContent
              user={user}
              mainNavItems={mainNavItems}
              onNavClick={() => setDrawerOpen(false)}
            />
          </aside>
        </div>
      )}
    </>
  );
}
