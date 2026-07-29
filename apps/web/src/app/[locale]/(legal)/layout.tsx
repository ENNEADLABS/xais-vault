import { setRequestLocale } from "next-intl/server";
import { MarketingNavbar } from "@/components/marketing/marketing-navbar";
import { MarketingFooter } from "@/components/marketing/marketing-footer";

interface LegalLayoutProps {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}

export default async function LegalLayout({ children, params }: LegalLayoutProps) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <div className="min-h-screen bg-vault-bg text-vault-text">
      <MarketingNavbar />
      {/* pt-24 compense la navbar fixed */}
      <main className="mx-auto max-w-3xl px-6 pt-24 pb-16">
        {children}
      </main>
      <MarketingFooter />
    </div>
  );
}
