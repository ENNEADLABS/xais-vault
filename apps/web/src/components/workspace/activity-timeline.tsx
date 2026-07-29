"use client";

import { useMemo } from "react";
import { useLocale } from "next-intl";
import {
  FileText,
  Shield,
  AlertTriangle,
  Search,
  Package,
  StickyNote,
} from "lucide-react";
import { cn, formatRelativeDate } from "@/lib/utils";
import type { Source, Insight, Investigation, Deliverable, Note } from "@/types/api";

// ─── Types ───────────────────────────────────────────────

interface ActivityEvent {
  type: "source" | "scan" | "insight" | "investigation" | "deliverable" | "note";
  title: string;
  timestamp: string;
  status?: string;
}

// ─── Construction de la timeline ─────────────────────────

export function buildTimeline(
  sources: Source[],
  insights: Insight[],
  investigations: Investigation[],
  deliverables: Deliverable[],
  notes: Note[],
): ActivityEvent[] {
  const events: ActivityEvent[] = [];

  for (const s of sources) {
    events.push({
      type: "source",
      title: `${s.name} ${s.status === "ready" ? "indexé" : s.status === "processing" ? "en cours" : "uploadé"}`,
      timestamp: s.created_at,
      status: s.status,
    });
  }

  for (const f of insights) {
    const label =
      f.status === "confirmed"
        ? "confirmé"
        : f.status === "rejected"
          ? "rejeté"
          : "détecté";
    events.push({
      type: "insight",
      title: `${f.title} — ${label}`,
      timestamp: f.updated_at ?? f.created_at,
      status: f.status,
    });
  }

  for (const inv of investigations) {
    const label =
      inv.status === "completed"
        ? "terminée"
        : inv.status === "processing"
          ? "en cours"
          : inv.status === "failed"
            ? "échouée"
            : "lancée";
    events.push({
      type: "investigation",
      title: `Investigation "${inv.question.slice(0, 50)}${inv.question.length > 50 ? "…" : ""}" ${label}`,
      timestamp: inv.completed_at ?? inv.started_at ?? inv.created_at,
      status: inv.status,
    });
  }

  for (const d of deliverables) {
    const label = d.status === "completed" ? "généré" : d.status === "processing" ? "en cours" : "lancé";
    events.push({
      type: "deliverable",
      title: `${d.name} ${label}`,
      timestamp: d.completed_at ?? d.created_at,
      status: d.status,
    });
  }

  for (const n of notes) {
    events.push({
      type: "note",
      title: n.title ?? "Note ajoutée",
      timestamp: n.created_at,
    });
  }

  // Trier par date desc
  events.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  return events;
}

// ─── Icônes par type ─────────────────────────────────────

const EVENT_CONFIG: Record<
  ActivityEvent["type"],
  { icon: typeof FileText; color: string }
> = {
  source: { icon: FileText, color: "text-vault-accent" },
  scan: { icon: Shield, color: "text-vault-success" },
  insight: { icon: AlertTriangle, color: "text-vault-warning" },
  investigation: { icon: Search, color: "text-vault-accent" },
  deliverable: { icon: Package, color: "text-teal-400" },
  note: { icon: StickyNote, color: "text-purple-400" },
};

// ─── Composant ───────────────────────────────────────────

interface ActivityTimelineProps {
  sources: Source[];
  insights: Insight[];
  investigations: Investigation[];
  deliverables: Deliverable[];
  notes: Note[];
  maxItems?: number;
}

export function ActivityTimeline({
  sources,
  insights,
  investigations,
  deliverables,
  notes,
  maxItems = 8,
}: ActivityTimelineProps) {
  const locale = useLocale();

  const events = useMemo(
    () =>
      buildTimeline(sources, insights, investigations, deliverables, notes).slice(
        0,
        maxItems,
      ),
    [sources, insights, investigations, deliverables, notes, maxItems],
  );

  if (events.length === 0) return null;

  return (
    <div className="relative pl-5">
      {/* Ligne verticale */}
      <div className="absolute left-[7px] top-1 bottom-1 w-px bg-vault-border" />

      <div className="space-y-3">
        {events.map((event, i) => {
          const config = EVENT_CONFIG[event.type];
          const Icon = config.icon;
          return (
            <div key={`${event.type}-${i}`} className="relative flex items-start gap-2.5">
              {/* Point sur la ligne */}
              <div
                className={cn(
                  "absolute -left-5 top-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-vault-surface border border-vault-border",
                )}
              >
                <Icon className={cn("h-2 w-2", config.color)} />
              </div>

              {/* Contenu */}
              <div className="flex-1 min-w-0">
                <p className="text-[12px] text-vault-text leading-snug truncate">
                  {event.title}
                </p>
              </div>

              {/* Date relative */}
              <span className="shrink-0 text-[11px] text-vault-text-muted whitespace-nowrap">
                {formatRelativeDate(event.timestamp, locale)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
