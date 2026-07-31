"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Key } from "lucide-react";
import { useApiKeys } from "@/lib/hooks/use-api-keys";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiKeyRow } from "./api-key-row";
import { CreateApiKeyDialog } from "./create-api-key-dialog";
import { ApiKeySecretDialog } from "./api-key-secret-dialog";

export function ApiKeysTab() {
  const t = useTranslations("settings");
  const { data, isLoading } = useApiKeys();
  const [createOpen, setCreateOpen] = useState(false);
  const [newKey, setNewKey] = useState<string | null>(null);

  function handleKeyCreated(key: string) {
    setNewKey(key);
    setCreateOpen(false);
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }

  const keys = data?.data ?? [];

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium">{t("apiKeys.title")}</h3>
          <p className="text-xs text-vault-text-muted mt-0.5">
            {t("apiKeys.description")}
          </p>
        </div>
        <Button size="sm" onClick={() => setCreateOpen(true)}>
          {t("apiKeys.create")}
        </Button>
      </div>

      {keys.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center border border-vault-border rounded-lg">
          <Key className="h-8 w-8 text-vault-text-muted mb-3" />
          <p className="text-sm font-medium">{t("apiKeys.noKeys")}</p>
          <p className="text-xs text-vault-text-muted mt-1">
            {t("apiKeys.noKeysHint")}
          </p>
        </div>
      ) : (
        <div className="border border-vault-border rounded-lg px-4">
          {keys.map((key) => (
            <ApiKeyRow key={key.id} apiKey={key} onRotated={handleKeyCreated} />
          ))}
        </div>
      )}

      <CreateApiKeyDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={handleKeyCreated}
      />

      <ApiKeySecretDialog secret={newKey} onClose={() => setNewKey(null)} />
    </div>
  );
}
