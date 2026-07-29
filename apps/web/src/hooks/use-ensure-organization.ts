"use client";

import { useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type ApiResponse } from "@/lib/api";
import { useUIStore } from "@/stores/ui-store";

interface OrgItem {
  id: string;
  name: string;
  slug: string;
}

export function useEnsureOrganization() {
  const { organizationId, setOrganizationId } = useUIStore();
  const queryClient = useQueryClient();

  const { data: orgsResponse, isLoading } = useQuery({
    queryKey: ["organizations"],
    queryFn: () => api.get<ApiResponse<OrgItem[]>>("/organizations/"),
  });

  const createOrgMutation = useMutation({
    mutationFn: () => {
      const slug = `org-${Date.now().toString(36)}`;
      return api.post("/organizations/", { name: "Mon espace", slug });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["organizations"] });
    },
  });

  useEffect(() => {
    if (isLoading) return;

    const orgList = orgsResponse?.data ?? [];

    if (
      orgList.length === 0 &&
      !createOrgMutation.isPending &&
      !createOrgMutation.isError
    ) {
      createOrgMutation.mutate();
      return;
    }

    const firstOrg = orgList[0];
    if (firstOrg && !organizationId) {
      setOrganizationId(firstOrg.id);
      api.setOrganizationId(firstOrg.id);
    }
  }, [
    orgsResponse,
    isLoading,
    organizationId,
    setOrganizationId,
    createOrgMutation,
  ]);

  return { isLoading: isLoading || createOrgMutation.isPending };
}
