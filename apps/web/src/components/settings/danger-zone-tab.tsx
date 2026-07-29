"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import {
  useOrganization,
  useDeleteOrganization,
  useLeaveOrganization,
} from "@/lib/hooks/use-organization";
import { useProfile } from "@/lib/hooks/use-profile";
import { useOrganizationMembers } from "@/lib/hooks/use-organization";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { DeleteOrgDialog } from "./delete-org-dialog";

interface DangerZoneTabProps {
  orgId: string;
}

export function DangerZoneTab({ orgId }: DangerZoneTabProps) {
  const t = useTranslations("settings");
  const { data: orgData } = useOrganization(orgId);
  const { data: profileData } = useProfile();
  const { data: membersData } = useOrganizationMembers(orgId);
  const deleteOrg = useDeleteOrganization(orgId);
  const leaveOrg = useLeaveOrganization(orgId);

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [leaveOpen, setLeaveOpen] = useState(false);

  const org = orgData?.data;
  const currentUserId = profileData?.data?.id;
  const members = membersData?.data ?? [];
  const currentMember = members.find((m) => m.user_id === currentUserId);
  const isAdmin = currentMember?.role === "admin";

  async function handleDelete() {
    try {
      await deleteOrg.mutateAsync();
      toast.success(t("danger.deleteOrgSuccess"));
    } catch {
      toast.error("Erreur lors de la suppression");
    }
  }

  async function handleLeave() {
    try {
      await leaveOrg.mutateAsync();
      toast.success(t("danger.leaveOrgSuccess"));
    } catch (err: unknown) {
      const msg =
        (err as { error?: { message?: string } })?.error?.message ?? "";
      toast.error(msg || "Erreur lors du départ");
    }
  }

  return (
    <div className="space-y-6 max-w-lg">
      <div className="rounded-md border border-destructive/30 p-4 space-y-4">
        <h3 className="text-sm font-semibold text-destructive">
          {t("danger.title")}
        </h3>

        {isAdmin ? (
          <div className="space-y-2">
            <p className="text-sm font-medium">{t("danger.deleteOrg")}</p>
            <p className="text-sm text-vault-text-muted">
              {t("danger.deleteOrgDescription")}
            </p>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setDeleteOpen(true)}
            >
              {t("danger.deleteOrgButton")}
            </Button>
          </div>
        ) : (
          <div className="space-y-2">
            <p className="text-sm font-medium">{t("danger.leaveOrg")}</p>
            <p className="text-sm text-vault-text-muted">
              {t("danger.leaveOrgDescription")}
            </p>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setLeaveOpen(true)}
            >
              {t("danger.leaveOrgButton")}
            </Button>
          </div>
        )}
      </div>

      <DeleteOrgDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        onConfirm={handleDelete}
        isLoading={deleteOrg.isPending}
        orgName={org?.name}
      />

      {/* Leave org dialog */}
      <Dialog open={leaveOpen} onOpenChange={setLeaveOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("danger.leaveOrg")}</DialogTitle>
            <DialogDescription>{t("danger.leaveOrgConfirm")}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setLeaveOpen(false)}>
              Annuler
            </Button>
            <Button
              variant="destructive"
              disabled={leaveOrg.isPending}
              onClick={handleLeave}
            >
              {leaveOrg.isPending
                ? t("danger.leaveOrgLeaving")
                : t("danger.leaveOrgButton")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
