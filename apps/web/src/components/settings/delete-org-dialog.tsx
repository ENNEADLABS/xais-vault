"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
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

interface DeleteOrgDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  isLoading: boolean;
  orgName: string | undefined;
}

export function DeleteOrgDialog({
  open,
  onOpenChange,
  onConfirm,
  isLoading,
  orgName,
}: DeleteOrgDialogProps) {
  const t = useTranslations("settings");
  const [confirmName, setConfirmName] = useState("");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("danger.deleteOrg")}</DialogTitle>
          <DialogDescription>
            {t("danger.deleteOrgDescription")}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2 py-2">
          <p className="text-sm">{t("danger.deleteOrgConfirm")}</p>
          <Input
            value={confirmName}
            onChange={(e) => setConfirmName(e.target.value)}
            placeholder={orgName}
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Annuler
          </Button>
          <Button
            variant="destructive"
            disabled={confirmName !== orgName || isLoading}
            onClick={onConfirm}
          >
            {isLoading
              ? t("danger.deleteOrgDeleting")
              : t("danger.deleteOrgButton")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
