"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "@/i18n/navigation";
import { api, type ApiResponse } from "@/lib/api";
import { useUIStore } from "@/stores/ui-store";
import { useProfile } from "@/lib/hooks/use-profile";
import type { ChatPersona, Organization, OrganizationMember } from "@/types/api";

export function useOrganization(orgId: string) {
  return useQuery({
    queryKey: ["organization", orgId],
    queryFn: () =>
      api.get<ApiResponse<Organization>>(`/organizations/${orgId}`),
    enabled: !!orgId,
  });
}

export function useOrganizationMembers(orgId: string) {
  return useQuery({
    queryKey: ["organization-members", orgId],
    queryFn: () =>
      api.get<ApiResponse<OrganizationMember[]>>(
        `/organizations/${orgId}/members`,
      ),
    enabled: !!orgId,
  });
}

export function useUpdateOrganization(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      name?: string;
      logo_url?: string;
      chat_persona?: ChatPersona;
    }) =>
      api.patch<ApiResponse<Organization>>(`/organizations/${orgId}`, data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["organization", orgId] });
    },
  });
}

export function useInviteMember(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { email: string; role: string }) =>
      api.post<ApiResponse<OrganizationMember>>(
        `/organizations/${orgId}/members/invite`,
        data,
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["organization-members", orgId] });
    },
  });
}

export function useUpdateMemberRole(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ memberId, role }: { memberId: string; role: string }) =>
      api.patch<ApiResponse<OrganizationMember>>(
        `/organizations/${orgId}/members/${memberId}`,
        { role },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["organization-members", orgId] });
    },
  });
}

export function useRemoveMember(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (memberId: string) =>
      api.delete(`/organizations/${orgId}/members/${memberId}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["organization-members", orgId] });
    },
  });
}

/** Retourne le rôle de l'utilisateur courant dans l'organisation. */
export function useCurrentOrgRole(orgId: string): "admin" | "analyst" | "viewer" | null {
  const { data: profileRes } = useProfile();
  const { data: membersRes } = useOrganizationMembers(orgId);

  const currentUserId = profileRes?.data?.id;
  const members = membersRes?.data ?? [];

  if (!currentUserId || members.length === 0) return null;
  const member = members.find((m) => m.user_id === currentUserId);
  return member?.role ?? null;
}

export function useLeaveOrganization(orgId: string) {
  const qc = useQueryClient();
  const router = useRouter();
  const setOrganizationId = useUIStore((s) => s.setOrganizationId);

  return useMutation({
    mutationFn: () => api.post(`/organizations/${orgId}/members/leave`),
    onSuccess: () => {
      setOrganizationId(null);
      void qc.invalidateQueries({ queryKey: ["organizations"] });
      router.push("/workspaces");
    },
  });
}

export function useDeleteOrganization(orgId: string) {
  const qc = useQueryClient();
  const router = useRouter();
  const setOrganizationId = useUIStore((s) => s.setOrganizationId);

  return useMutation({
    mutationFn: () => api.delete(`/organizations/${orgId}`),
    onSuccess: () => {
      setOrganizationId(null);
      void qc.invalidateQueries({ queryKey: ["organizations"] });
      router.push("/workspaces");
    },
  });
}
