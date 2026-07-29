"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import {
  useOrganization,
  useUpdateOrganization,
} from "@/lib/hooks/use-organization";
import { useProfile } from "@/lib/hooks/use-profile";
import { useOrganizationMembers } from "@/lib/hooks/use-organization";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import type { ChatPersona } from "@/types/api";
import { MembersList } from "./members-list";
import { InviteMemberDialog } from "./invite-member-dialog";

interface OrganizationTabProps {
  orgId: string;
}

const PLAN_CLASSES: Record<string, string> = {
  starter: "bg-vault-border/40 text-vault-text-secondary",
  premium: "bg-vault-accent-dim text-vault-accent",
  trial: "bg-vault-border/40 text-vault-text-muted",
  team: "bg-vault-accent-dim text-vault-accent",
  enterprise: "bg-vault-accent-dim text-vault-accent",
};

export function OrganizationTab({ orgId }: OrganizationTabProps) {
  const t = useTranslations("settings");
  const { data: orgData, isLoading } = useOrganization(orgId);
  const { data: profileData } = useProfile();
  const { data: membersData } = useOrganizationMembers(orgId);
  const updateOrg = useUpdateOrganization(orgId);

  const [name, setName] = useState("");
  const [inviteOpen, setInviteOpen] = useState(false);

  const org = orgData?.data;
  const currentUserId = profileData?.data?.id;
  const members = membersData?.data ?? [];
  const currentMember = members.find((m) => m.user_id === currentUserId);
  const isAdmin = currentMember?.role === "admin";

  useEffect(() => {
    if (org) setName(org.name);
  }, [org]);

  async function handleSave() {
    try {
      await updateOrg.mutateAsync({ name });
      toast.success(t("organization.saved"));
    } catch {
      toast.error("Erreur lors de la mise à jour");
    }
  }

  async function handlePersonaChange(value: ChatPersona) {
    try {
      await updateOrg.mutateAsync({ chat_persona: value });
      toast.success(t("organization.chatPersonaSaved"));
    } catch {
      toast.error("Erreur lors de la mise à jour");
    }
  }

  const currentPersona: ChatPersona = org?.chat_persona ?? "general";

  if (isLoading) {
    return (
      <div className="space-y-4 max-w-md">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-2xl">
      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="org-name">{t("organization.name")}</Label>
          <div className="flex gap-2">
            <Input
              id="org-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={!isAdmin}
            />
            {isAdmin && (
              <Button onClick={handleSave} disabled={updateOrg.isPending}>
                {updateOrg.isPending
                  ? t("organization.saving")
                  : t("organization.save")}
              </Button>
            )}
          </div>
        </div>

        <div className="space-y-2">
          <Label>{t("organization.slug")}</Label>
          <Input
            value={org?.slug ?? ""}
            disabled
            className="text-vault-text-muted"
          />
          <p className="text-xs text-vault-text-muted">
            {t("organization.slugReadOnly")}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm text-vault-text-muted">
            {t("organization.plan")} :
          </span>
          <span className={cn("rounded px-2 py-0.5 font-mono text-[11px] uppercase tracking-wide", PLAN_CLASSES[org?.plan ?? "starter"] ?? "bg-vault-border/40 text-vault-text-secondary")}>
            {t(
              `organization.plan${(org?.plan ?? "starter").charAt(0).toUpperCase()}${(org?.plan ?? "starter").slice(1)}`,
            )}
          </span>
        </div>

        <div className="space-y-2">
          <Label htmlFor="org-chat-persona">
            {t("organization.chatPersonaLabel")}
          </Label>
          <Select
            value={currentPersona}
            onValueChange={(v) => handlePersonaChange(v as ChatPersona)}
            disabled={!isAdmin || updateOrg.isPending}
          >
            <SelectTrigger id="org-chat-persona" className="max-w-xs">
              <SelectValue>
                {currentPersona === "dd"
                  ? t("organization.chatPersonaDd")
                  : t("organization.chatPersonaGeneral")}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="general">
                {t("organization.chatPersonaGeneral")}
              </SelectItem>
              <SelectItem value="dd">
                {t("organization.chatPersonaDd")}
              </SelectItem>
            </SelectContent>
          </Select>
          <p className="text-xs text-vault-text-muted">
            {t("organization.chatPersonaHelp")}
          </p>
        </div>
      </div>

      <Separator />

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium">{t("organization.members")}</h3>
          {isAdmin && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => setInviteOpen(true)}
            >
              {t("organization.invite")}
            </Button>
          )}
        </div>
        <MembersList orgId={orgId} isAdmin={isAdmin} />
      </div>

      <InviteMemberDialog
        orgId={orgId}
        open={inviteOpen}
        onOpenChange={setInviteOpen}
      />
    </div>
  );
}
