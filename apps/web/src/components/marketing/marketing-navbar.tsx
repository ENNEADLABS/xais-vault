"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { Menu, X } from "lucide-react";
import Link from "next/link";
import { VaultLogo } from "@/components/ui/vault-logo";

export function MarketingNavbar() {
  const t = useTranslations("landing.nav");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 20);
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const navLinks = [
    { href: "#features", label: t("features") },
    { href: "#how-it-works", label: t("howItWorks") },
    { href: "#pricing", label: t("pricing") },
  ];

  return (
    <nav
      className={`fixed top-0 z-50 w-full border-b backdrop-blur-md transition-all duration-300 ${
        scrolled
          ? "border-vault-accent/15 bg-vault-bg/90 shadow-[0_1px_12px_rgba(6,182,212,0.06)]"
          : "border-vault-border bg-vault-bg/80"
      }`}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
        <Link href="/">
          <VaultLogo size="lg" />
        </Link>

        <div className="hidden items-center gap-8 md:flex">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="font-mono text-[13px] uppercase tracking-wider text-vault-text-secondary transition-colors hover:text-vault-text"
            >
              {link.label}
            </a>
          ))}
          <Link
            href="/login"
            className="cta-glow rounded-none bg-vault-accent px-6 py-2 font-mono text-[13px] font-medium uppercase tracking-wider text-black transition-colors hover:bg-vault-accent-hover"
          >
            {t("cta")}
          </Link>
        </div>

        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="text-vault-text-secondary md:hidden"
          aria-label="Menu"
        >
          {mobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {mobileOpen && (
        <div className="border-t border-vault-border bg-vault-bg px-6 py-4 md:hidden">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              onClick={() => setMobileOpen(false)}
              className="block py-3 font-mono text-[13px] uppercase tracking-wider text-vault-text-secondary"
            >
              {link.label}
            </a>
          ))}
          <Link
            href="/login"
            className="mt-2 block rounded-none bg-vault-accent px-6 py-2 text-center font-mono text-[13px] font-medium uppercase tracking-wider text-black"
          >
            {t("cta")}
          </Link>
        </div>
      )}
    </nav>
  );
}
