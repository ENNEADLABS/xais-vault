import { Skeleton } from "@/components/ui/skeleton";

export function InvestigationCardSkeleton() {
  return (
    <div
      className="rounded-lg border border-vault-border bg-vault-surface p-3 space-y-2"
      aria-hidden="true"
    >
      {/* Status + scope badges */}
      <div className="flex items-center gap-2">
        <Skeleton className="h-5 w-18 rounded-full" />
        <Skeleton className="h-5 w-14 rounded-full" />
      </div>
      {/* Question title */}
      <Skeleton className="h-4 w-4/5" />
      {/* Content placeholder (3 lines) */}
      <div className="space-y-1.5">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-5/6" />
        <Skeleton className="h-3 w-4/6" />
      </div>
    </div>
  );
}
