"use client";

import { useTranslations } from "next-intl";
import { usePathname, Link, useRouter } from "@/i18n/navigation";
import { useLocale } from "next-intl";
import { Settings, Key, Webhook, PanelLeftClose, PanelLeftOpen, Shield } from "lucide-react";
import { useSuperAdminCheck } from "@/lib/hooks/use-super-admin";
import { UserMenu } from "./user-menu";
import { NavLink } from "./nav-link";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { VaultLogo } from "@/components/ui/vault-logo";
import { cn } from "@/lib/utils";
import type { User } from "@supabase/supabase-js";

interface SidebarContentProps {
  user: User;
  onNavClick?: () => void;
  mainNavItems: Array<{ href: string; labelKey: string; icon: React.ElementType }>;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function SidebarContent({
  user,
  onNavClick,
  mainNavItems,
  collapsed = false,
  onToggleCollapse,
}: SidebarContentProps) {
  const t = useTranslations("nav");
  const pathname = usePathname();
  const locale = useLocale();
  const router = useRouter();
  const { data: superAdminData } = useSuperAdminCheck();

  function switchLocale(newLocale: string) {
    router.replace(pathname, { locale: newLocale });
  }

  return (
    <>
      {/* Logo */}
      <div className={cn("flex h-14 items-center", collapsed ? "justify-center px-0" : "px-4")}>
        <Link href="/workspaces">
          <VaultLogo size={collapsed ? "sm" : "md"} showText={!collapsed} />
        </Link>
      </div>

      <div className={cn("border-b border-vault-border", collapsed ? "mx-2" : "mx-4")} />

      {/* Nav principale */}
      <nav className="space-y-0.5 px-0 py-3">
        {mainNavItems.map(({ href, labelKey, icon: Icon }) => (
          <NavLink
            key={href + labelKey}
            href={href}
            labelKey={labelKey}
            icon={Icon}
            pathname={pathname}
            onNavClick={onNavClick}
            collapsed={collapsed}
          />
        ))}
      </nav>

      {/* Section WORKSPACE */}
      <div className="mt-2">
        {!collapsed && (
          <p className="px-4 pb-1.5 font-mono text-[11px] uppercase tracking-widest text-vault-text-muted">
            {t("workspace")}
          </p>
        )}
        <nav className="space-y-0.5">
          <NavLink href="/settings" labelKey="settings" icon={Settings} pathname={pathname} onNavClick={onNavClick} exact collapsed={collapsed} />
          <NavLink href="/settings" labelKey="apiKeys" icon={Key} pathname={pathname} onNavClick={onNavClick} exact collapsed={collapsed} />
          <NavLink href="/settings" labelKey="webhooks" icon={Webhook} pathname={pathname} onNavClick={onNavClick} exact collapsed={collapsed} />
        </nav>
      </div>

      {/* Lien Super Admin (visible uniquement pour les super-admins) */}
      {superAdminData?.is_super_admin && (
        <div className="mt-2">
          {!collapsed && (
            <div className={cn("border-t border-vault-border mx-4 mb-2")} />
          )}
          <nav className="space-y-0.5">
            <NavLink href="/super-admin" labelKey="superAdmin" icon={Shield} pathname={pathname} onNavClick={onNavClick} collapsed={collapsed} />
          </nav>
        </div>
      )}

      <div className="flex-1" />

      {/* Language switcher + theme toggle */}
      {!collapsed ? (
        <div className="px-4 pb-2 flex items-center gap-1">
          <button
            type="button"
            onClick={() => switchLocale("fr")}
            className={cn(
              "font-mono text-[11px] uppercase tracking-wider transition-colors",
              locale === "fr" ? "text-vault-text font-medium" : "text-vault-text-muted hover:text-vault-text-secondary",
            )}
          >
            FR
          </button>
          <span className="text-vault-text-muted text-[11px]">/</span>
          <button
            type="button"
            onClick={() => switchLocale("en")}
            className={cn(
              "font-mono text-[11px] uppercase tracking-wider transition-colors",
              locale === "en" ? "text-vault-text font-medium" : "text-vault-text-muted hover:text-vault-text-secondary",
            )}
          >
            EN
          </button>
          <div className="ml-auto">
            <ThemeToggle />
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-2 pb-2">
          <ThemeToggle />
        </div>
      )}

      {/* Toggle collapse (desktop only) */}
      {onToggleCollapse && (
        <div className={cn("border-t border-vault-border", collapsed ? "flex justify-center p-2" : "px-3 py-2")}>
          <button
            type="button"
            onClick={onToggleCollapse}
            className="rounded p-1.5 text-vault-text-muted hover:text-vault-text transition-colors"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? (
              <PanelLeftOpen className="h-4 w-4" />
            ) : (
              <PanelLeftClose className="h-4 w-4" />
            )}
          </button>
        </div>
      )}

      {/* User menu */}
      <div className={cn("border-t border-vault-border", collapsed ? "p-1" : "p-2")}>
        <UserMenu user={user} collapsed={collapsed} />
      </div>
    </>
  );
}
