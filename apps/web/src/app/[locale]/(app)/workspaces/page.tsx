import { setRequestLocale } from "next-intl/server";
import { WorkspacesPageClient } from "@/components/workspaces/workspaces-page-client";

export default async function WorkspacesPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  return (
    <div className="flex flex-col gap-4 p-6 md:p-8">
      <WorkspacesPageClient />
    </div>
  );
}
