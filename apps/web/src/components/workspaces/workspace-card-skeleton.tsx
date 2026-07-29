import { Skeleton } from "@/components/ui/skeleton";

export function WorkspaceCardSkeleton() {
  return (
    <div
      className="flex flex-col overflow-hidden border border-vault-border border-l-2 border-l-vault-text-muted/30 bg-vault-surface rounded-lg"
      role="status"
      aria-busy="true"
      aria-hidden="true"
    >
      {/* Header — match workspace-card: pl-4 pr-3 pt-3 pb-2 */}
      <div className="pl-4 pr-3 pt-3 pb-2">
        <div className="flex items-start gap-2.5">
          <Skeleton className="h-7 w-7 shrink-0 rounded" />
          <div className="min-w-0 flex-1 space-y-1.5">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
          {/* Scan status tag placeholder */}
          <Skeleton className="h-5 w-16 shrink-0" />
        </div>
      </div>

      {/* Footer — match workspace-card: 3 items */}
      <div className="mt-auto flex justify-between border-t border-vault-border bg-vault-surface-active px-4 py-2">
        <Skeleton className="h-3 w-16" />
        <Skeleton className="h-3 w-16" />
        <Skeleton className="h-3 w-14" />
      </div>
    </div>
  );
}
