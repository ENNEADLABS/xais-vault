"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface NavLinkProps {
  href: string;
  labelKey: string;
  icon: React.ElementType;
  pathname: string;
  onNavClick?: () => void;
  exact?: boolean;
  collapsed?: boolean;
}

export function NavLink({
  href,
  labelKey,
  icon: Icon,
  pathname,
  onNavClick,
  exact = false,
  collapsed = false,
}: NavLinkProps) {
  const t = useTranslations("nav");
  const isActive = exact ? pathname === href : pathname.startsWith(href);
  const label = t(labelKey as "workspaces" | "settings" | "apiKeys" | "webhooks" | "superAdmin");

  const linkContent = (
    <Link
      href={href as Parameters<typeof Link>[0]["href"]}
      onClick={onNavClick}
      className={cn(
        "flex items-center rounded-md font-mono text-[12px] uppercase tracking-wide transition-colors duration-150 mx-1",
        collapsed ? "justify-center py-2 px-0" : "gap-3 py-1.5 px-3",
        isActive
          ? "border-l-2 border-vault-accent bg-vault-accent-dim text-vault-text pl-2.5"
          : "border-l-2 border-transparent text-vault-text-muted hover:text-vault-text-secondary pl-2.5",
        collapsed && "border-l-0 pl-0",
      )}
    >
      <Icon className="h-3.5 w-3.5 shrink-0" />
      {!collapsed && label}
    </Link>
  );

  if (collapsed) {
    return (
      <Tooltip>
        <TooltipTrigger
          render={
            <Link
              href={href as Parameters<typeof Link>[0]["href"]}
              onClick={onNavClick}
              className={cn(
                "flex items-center justify-center rounded-md py-2 mx-1 transition-colors duration-150",
                isActive
                  ? "bg-vault-accent-dim text-vault-text"
                  : "text-vault-text-muted hover:text-vault-text-secondary",
              )}
            />
          }
        >
          <Icon className="h-3.5 w-3.5 shrink-0" />
        </TooltipTrigger>
        <TooltipContent side="right">{label}</TooltipContent>
      </Tooltip>
    );
  }

  return linkContent;
}
