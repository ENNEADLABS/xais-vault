"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useWorkspaces } from "@/lib/hooks/use-workspaces";
import { WorkspacesToolbar } from "./workspaces-toolbar";
import { WorkspaceCard } from "./workspace-card";
import { WorkspaceCardSkeleton } from "./workspace-card-skeleton";
import { WorkspacesEmptyState } from "./workspaces-empty-state";
import { WorkspaceCreateDialog } from "./workspace-create-dialog";
import { ErrorState } from "@/components/ui/error-state";

type StatusFilter = "active" | "archived" | "closed" | null;

export function WorkspacesPageClient() {
  const t = useTranslations("workspaces");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<StatusFilter>(null);
  const [emptyDialogOpen, setEmptyDialogOpen] = useState(false);

  const { data, isLoading, isError } = useWorkspaces({ status });
  const workspaces = data?.data ?? [];

  const filtered = search
    ? workspaces.filter((d) => {
        const q = search.toLowerCase();
        return (
          d.name.toLowerCase().includes(q) ||
          d.target_company?.toLowerCase().includes(q)
        );
      })
    : workspaces;

  if (isLoading) {
    return (
      <div className="space-y-4">
        <WorkspacesToolbar
          search={search}
          onSearchChange={setSearch}
          status={status}
          onStatusChange={setStatus}
        />
        <div className="grid grid-cols-[repeat(auto-fill,minmax(320px,1fr))] gap-4" role="status" aria-busy="true">
          {Array.from({ length: 6 }).map((_, i) => (
            <WorkspaceCardSkeleton key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return <ErrorState title="LOAD_FAILED" onRetry={() => window.location.reload()} />;
  }

  return (
    <div className="space-y-4">
      <WorkspacesToolbar
        search={search}
        onSearchChange={setSearch}
        status={status}
        onStatusChange={setStatus}
      />

      {filtered.length === 0 && !search ? (
        <>
          <WorkspacesEmptyState onCreateClick={() => setEmptyDialogOpen(true)} />
          <WorkspaceCreateDialog
            open={emptyDialogOpen}
            onOpenChange={setEmptyDialogOpen}
          />
        </>
      ) : filtered.length === 0 ? (
        <p className="py-8 text-center text-sm text-vault-text-muted">
          {t("emptyState")}
        </p>
      ) : (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(320px,1fr))] gap-4">
          {filtered.map((workspace, index) => (
            <div
              key={workspace.id}
              className="animate-slide-up"
              style={{
                animationDelay: `${index * 50}ms`,
                animationFillMode: "backwards",
              }}
            >
              <WorkspaceCard workspace={workspace} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
