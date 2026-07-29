import { Skeleton } from "@/components/ui/skeleton";

export function InsightCardSkeleton() {
  return (
    <div
      className="rounded-lg border border-vault-border border-l-2 border-l-vault-text-muted/30 bg-vault-surface p-3 space-y-2"
      aria-hidden="true"
    >
      {/* Badges — severity, type, status */}
      <div className="flex items-center gap-2">
        <Skeleton className="h-5 w-16 rounded" />
        <Skeleton className="h-5 w-20 rounded" />
        <Skeleton className="ml-auto h-5 w-16 rounded" />
      </div>
      {/* Title */}
      <Skeleton className="h-4 w-3/4" />
      {/* Description (2 lines) */}
      <div className="space-y-1.5">
        <Skeleton className="h-3.5 w-full" />
        <Skeleton className="h-3.5 w-5/6" />
      </div>
      {/* Confidence bar */}
      <div className="flex items-center gap-2">
        <Skeleton className="h-1 flex-1 rounded-full" />
        <Skeleton className="h-3 w-8" />
      </div>
    </div>
  );
}
