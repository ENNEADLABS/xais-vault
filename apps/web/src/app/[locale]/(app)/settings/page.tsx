import { setRequestLocale } from "next-intl/server";
import { SettingsTabs } from "@/components/settings/settings-tabs";

export default async function SettingsPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  return (
    <div className="flex h-full min-h-0">
      <SettingsTabs />
    </div>
  );
}
