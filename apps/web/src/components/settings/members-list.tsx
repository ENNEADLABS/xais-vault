"use client";

import { useTranslations } from "next-intl";
import { toast } from "sonner";
import {
  useOrganizationMembers,
  useUpdateMemberRole,
  useRemoveMember,
} from "@/lib/hooks/use-organization";
import { useProfile } from "@/lib/hooks/use-profile";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { OrganizationMember } from "@/types/api";

interface MembersListProps {
  orgId: string;
  isAdmin: boolean;
}

export function MembersList({ orgId, isAdmin }: MembersListProps) {
  const t = useTranslations("settings");
  const { data: membersData, isLoading } = useOrganizationMembers(orgId);
  const { data: profileData } = useProfile();
  const updateRole = useUpdateMemberRole(orgId);
  const removeMember = useRemoveMember(orgId);

  const members = membersData?.data ?? [];
  const currentUserId = profileData?.data?.id;

  async function handleRoleChange(member: OrganizationMember, newRole: string) {
    try {
      await updateRole.mutateAsync({ memberId: member.id, role: newRole });
    } catch {
      toast.error("Erreur lors du changement de rôle");
    }
  }

  async function handleRemove(member: OrganizationMember) {
    const name = member.display_name ?? member.email ?? member.user_id;
    if (!confirm(t("organization.removeMemberConfirm", { name }))) return;
    try {
      await removeMember.mutateAsync(member.id);
      toast.success(t("organization.memberRemoved"));
    } catch {
      toast.error("Erreur lors de la suppression du membre");
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  if (!members.length) {
    return (
      <p className="text-sm text-vault-text-muted">
        {t("organization.noMembers")}
      </p>
    );
  }

  return (
    <div className="divide-y divide-vault-border rounded-md border border-vault-border">
      {members.map((member) => {
        const isCurrentUser = member.user_id === currentUserId;
        const displayName =
          member.display_name ?? member.email ?? member.user_id;

        return (
          <div
            key={member.id}
            className="flex items-center justify-between px-4 py-3"
          >
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">
                {displayName}
                {isCurrentUser && (
                  <span className="ml-1 text-vault-text-muted text-xs">
                    {t("organization.you")}
                  </span>
                )}
              </p>
              {member.email && member.display_name && (
                <p className="truncate text-xs text-vault-text-muted">
                  {member.email}
                </p>
              )}
            </div>

            <div className="ml-4 flex items-center gap-2 shrink-0">
              <span className="rounded bg-vault-border/40 px-2 py-0.5 font-mono text-[11px] uppercase tracking-wide text-vault-text-secondary">
                {t(
                  `organization.role${member.role.charAt(0).toUpperCase()}${member.role.slice(1)}`,
                )}
              </span>

              {isAdmin && !isCurrentUser && (
                <DropdownMenu>
                  <DropdownMenuTrigger
                    render={
                      <Button variant="ghost" size="sm" className="h-7 px-2">
                        ···
                      </Button>
                    }
                  />
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      onClick={() => handleRoleChange(member, "admin")}
                    >
                      {t("organization.roleAdmin")}
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => handleRoleChange(member, "analyst")}
                    >
                      {t("organization.roleAnalyst")}
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => handleRoleChange(member, "viewer")}
                    >
                      {t("organization.roleViewer")}
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      className="text-destructive"
                      onClick={() => handleRemove(member)}
                    >
                      {t("organization.removeMember")}
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
