export const dynamic = "force-dynamic";

import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { AppShell } from "./app-shell";
import { PendingCheckoutTrigger } from "@/components/billing/pending-checkout-trigger";
import { setRequestLocale } from "next-intl/server";

export default async function AppLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  return (
    <div className="flex h-screen">
      <AppSidebar user={user} />
      <main className="flex-1 overflow-auto pt-14 md:pt-0">
        <AppShell>{children}</AppShell>
      </main>
      <PendingCheckoutTrigger />
    </div>
  );
}
