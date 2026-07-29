import { setRequestLocale } from "next-intl/server";
import { WorkspacePageLayout } from "@/components/workspace/workspace-page-layout";

export default async function WorkspacePage({
  params,
}: {
  params: Promise<{ locale: string; workspaceId: string }>;
}) {
  const { locale, workspaceId } = await params;
  setRequestLocale(locale);

  return <WorkspacePageLayout workspaceId={workspaceId} />;
}
