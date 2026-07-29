import { Skeleton } from "@/components/ui/skeleton";

export function SourceCardSkeleton() {
  return (
    <div className="flex items-center gap-2 rounded p-2.5" aria-hidden="true">
      {/* Icon box — match source-card: h-8 w-8 rounded-md bg */}
      <Skeleton className="h-8 w-8 shrink-0 rounded-md" />
      <div className="min-w-0 flex-1 space-y-1.5">
        <Skeleton className="h-4 w-3/4" />
        <div className="flex items-center gap-1.5">
          <Skeleton className="h-4 w-14 rounded" />
          <Skeleton className="h-3 w-10" />
        </div>
      </div>
    </div>
  );
}
