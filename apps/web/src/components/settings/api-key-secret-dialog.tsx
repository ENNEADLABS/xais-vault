"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { Copy, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface ApiKeySecretDialogProps {
  secret: string | null;
  onClose: () => void;
}

export function ApiKeySecretDialog({
  secret,
  onClose,
}: ApiKeySecretDialogProps) {
  const t = useTranslations("settings");
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    if (!secret) return;
    await navigator.clipboard.writeText(secret);
    toast.success(t("apiKeys.copied"));
    setCopied(true);
  }

  function handleClose() {
    setCopied(false);
    onClose();
  }

  return (
    <Dialog open={!!secret} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent showCloseButton={false}>
        <DialogHeader>
          <DialogTitle>{t("apiKeys.secretTitle")}</DialogTitle>
          <DialogDescription>
            <span className="flex items-start gap-2 text-amber-600 dark:text-amber-400">
              <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
              <span>{t("apiKeys.secretWarning")}</span>
            </span>
          </DialogDescription>
        </DialogHeader>

        <div className="flex gap-2">
          <Input value={secret ?? ""} readOnly className="font-mono text-sm" />
          <Button variant="outline" size="icon" onClick={handleCopy}>
            <Copy className="h-4 w-4" />
          </Button>
        </div>

        <DialogFooter>
          <Button onClick={handleClose} disabled={!copied} className="w-full">
            {t("apiKeys.done")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
