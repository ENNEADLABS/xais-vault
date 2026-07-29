"use client";

import { useTranslations, useLocale } from "next-intl";
import { useRouter, usePathname } from "@/i18n/navigation";
import { Globe, LogOut, Settings } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { User } from "@supabase/supabase-js";

interface UserMenuProps {
  user: User;
  collapsed?: boolean;
}

export function UserMenu({ user, collapsed = false }: UserMenuProps) {
  const t = useTranslations("userMenu");
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const supabase = createClient();

  const displayName =
    (user.user_metadata?.full_name as string | undefined) ||
    user.email ||
    "User";
  const initials = displayName
    .split(" ")
    .map((n: string) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  async function handleLogout() {
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  function switchLocale(newLocale: string) {
    router.replace(pathname, { locale: newLocale });
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className={`flex w-full items-center rounded-md text-sm transition-colors hover:bg-vault-surface-hover ${collapsed ? "justify-center p-2" : "gap-3 px-3 py-2"}`}>
        <Avatar className="h-7 w-7">
          <AvatarFallback className="bg-vault-accent/20 text-vault-accent text-xs font-mono">
            {initials}
          </AvatarFallback>
        </Avatar>
        {!collapsed && (
          <span className="flex-1 truncate text-left text-vault-text-secondary font-mono text-[12px]">
            {displayName}
          </span>
        )}
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" side="top" className="w-56">
        <DropdownMenuLabel className="truncate text-xs font-normal text-muted-foreground">
          {user.email}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => router.push("/settings")}>
          <Settings className="mr-2 h-4 w-4" />
          {t("settings")}
        </DropdownMenuItem>
        <DropdownMenuSub>
          <DropdownMenuSubTrigger>
            <Globe className="mr-2 h-4 w-4" />
            {t("language")}
          </DropdownMenuSubTrigger>
          <DropdownMenuSubContent>
            <DropdownMenuItem onClick={() => switchLocale("fr")}>
              {t("languageFr")} {locale === "fr" && "✓"}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => switchLocale("en")}>
              {t("languageEn")} {locale === "en" && "✓"}
            </DropdownMenuItem>
          </DropdownMenuSubContent>
        </DropdownMenuSub>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={handleLogout}
          className="text-destructive focus:text-destructive"
        >
          <LogOut className="mr-2 h-4 w-4" />
          {t("logout")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
