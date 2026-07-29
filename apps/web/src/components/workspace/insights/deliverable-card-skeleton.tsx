import { Skeleton } from "@/components/ui/skeleton";

export function DeliverableCardSkeleton() {
  return (
    <div
      className="rounded-lg border border-vault-border bg-vault-surface p-3 space-y-2"
      aria-hidden="true"
    >
      {/* Type + status badges */}
      <div className="flex items-center gap-2">
        <Skeleton className="h-5 w-20 rounded-full" />
        <Skeleton className="ml-auto h-5 w-16 rounded-full" />
      </div>
      {/* Title */}
      <Skeleton className="h-4 w-3/4" />
      {/* Progress bar (processing state) */}
      <div className="flex items-center gap-2">
        <Skeleton className="h-1.5 flex-1 rounded-full" />
        <Skeleton className="h-3 w-8" />
      </div>
      {/* Timestamp footer */}
      <Skeleton className="h-3 w-24" />
    </div>
  );
}
