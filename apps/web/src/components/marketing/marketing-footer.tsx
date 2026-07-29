"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { VaultLogo } from "@/components/ui/vault-logo";

export function MarketingFooter() {
  const t = useTranslations("landing.footer");

  return (
    <footer className="border-t border-vault-border bg-vault-bg py-10">
      <div className="mx-auto max-w-7xl px-6">
        <div className="flex flex-col items-center justify-between gap-6 md:flex-row">
          <VaultLogo size="sm" />

          <div className="flex flex-wrap justify-center gap-6">
            <Link
              href="/login"
              className="font-mono text-[12px] text-vault-text-muted transition-colors hover:text-vault-text"
            >
              {t("login")}
            </Link>
            <a
              href="mailto:contact@xaisoluces.com"
              className="font-mono text-[12px] text-vault-text-muted transition-colors hover:text-vault-text"
            >
              {t("contact")}
            </a>
            <Link
              href="/privacy"
              className="font-mono text-[12px] text-vault-text-muted transition-colors hover:text-vault-text"
            >
              {t("privacy")}
            </Link>
            <Link
              href="/terms"
              className="font-mono text-[12px] text-vault-text-muted transition-colors hover:text-vault-text"
            >
              {t("terms")}
            </Link>
            <Link
              href="/legal"
              className="font-mono text-[12px] text-vault-text-muted transition-colors hover:text-vault-text"
            >
              {t("legal")}
            </Link>
          </div>
        </div>

        <div className="mt-8 border-t border-vault-border pt-6 text-center">
          <p className="font-mono text-[11px] text-vault-text-muted/60">
            {t("copyright")}
          </p>
        </div>
      </div>
    </footer>
  );
}
