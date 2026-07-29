export const dynamic = "force-dynamic";

import { setRequestLocale, getTranslations } from "next-intl/server";
import { VaultLogo } from "@/components/ui/vault-logo";

export default async function AuthLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "auth.branding" });

  // Métriques marketing statiques — values gérées via les traductions
  const metrics = [
    { value: t("metricDossiersValue"), label: t("metricDossiers") },
    { value: t("metricWorkspacesValue"), label: t("metricWorkspaces") },
    { value: t("metricPrecisionValue"), label: t("metricPrecision") },
    { value: t("metricSpeedValue"), label: t("metricSpeed") },
  ];

  return (
    <div className="flex min-h-screen bg-vault-bg">
      {/* Côté gauche — branding (desktop uniquement) */}
      <div className="relative hidden w-[40%] flex-col justify-between overflow-hidden border-r border-vault-border p-12 lg:flex">
        <div className="pointer-events-none absolute inset-0 vault-grid-pattern" />
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_oklch(0.65_0.143_215_/_0.08)_0%,_transparent_60%)]" />

        <div className="relative">
          <p className="font-mono text-xs tracking-[0.3em] text-vault-text-secondary uppercase">
            {t("tagline")}
          </p>
        </div>

        <div className="relative space-y-6">
          <VaultLogo size="xl" />
          <p className="max-w-xs text-base leading-relaxed text-vault-text-secondary">
            {t("description")}
          </p>

          <div className="grid grid-cols-2 gap-4 pt-4">
            {metrics.map((m) => (
              <div key={m.label} className="border border-vault-border bg-vault-surface/50 p-4">
                <p className="font-mono text-2xl font-semibold text-vault-accent">{m.value}</p>
                <p className="mt-1 text-xs text-vault-text-secondary">{m.label}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="relative">
          <p className="font-mono text-xs tracking-[0.2em] text-vault-text-secondary/50 uppercase">
            {t("copyright")}
          </p>
        </div>
      </div>

      {/* Côté droit — formulaire */}
      <div className="flex w-full flex-col items-center justify-center bg-vault-surface px-6 py-12 lg:w-[60%]">
        <div className="mb-10 lg:hidden">
          <VaultLogo size="xl" />
        </div>

        <div className="w-full max-w-md">{children}</div>
      </div>
    </div>
  );
}
