"use client";

import { useMemo } from "react";
import { cn } from "@/lib/utils";
import type { Insight, Investigation, Deliverable } from "@/types/api";

// ─── Calcul du Workspace Score ────────────────────────────────

export function computeWorkspaceScore(
  insights: Insight[],
  investigations: Investigation[],
  deliverables: Deliverable[],
): number {
  let score = 70;

  // Pénalités par insight non résolu
  const unresolved = insights.filter((f) => f.status === "pending");
  score -= unresolved.filter((f) => f.severity === "critical").length * 8;
  score -= unresolved.filter((f) => f.severity === "high").length * 4;
  score -= unresolved.filter((f) => f.severity === "medium").length * 2;

  // Bonus : insights traités (confirmed ou rejected)
  const treated = insights.filter(
    (f) => f.status === "confirmed" || f.status === "rejected",
  );
  if (insights.length > 0) {
    score += (treated.length / insights.length) * 15;
  }

  // Bonus investigations complétées (max +10)
  const completedInv = investigations.filter((i) => i.status === "completed");
  score += Math.min(completedInv.length * 3, 10);

  // Bonus livrables générés (max +5)
  const completedDel = deliverables.filter((d) => d.status === "completed");
  score += Math.min(completedDel.length * 2, 5);

  return Math.max(0, Math.min(100, Math.round(score)));
}

// ─── Label et couleur ────────────────────────────────────

function getScoreColor(score: number) {
  if (score < 40) return { ring: "text-vault-danger", bg: "text-vault-danger" };
  if (score < 60) return { ring: "text-vault-warning", bg: "text-vault-warning" };
  return { ring: "text-vault-success", bg: "text-vault-success" };
}

function getScoreLabel(score: number) {
  if (score < 40) return "Risqué";
  if (score < 60) return "Modéré";
  return "Favorable";
}

// ─── Composant cercle animé ──────────────────────────────

interface WorkspaceScoreProps {
  insights: Insight[];
  investigations: Investigation[];
  deliverables: Deliverable[];
  size?: "sm" | "lg";
}

export function WorkspaceScore({
  insights,
  investigations,
  deliverables,
  size = "lg",
}: WorkspaceScoreProps) {
  const score = useMemo(
    () => computeWorkspaceScore(insights, investigations, deliverables),
    [insights, investigations, deliverables],
  );

  const colors = getScoreColor(score);
  const label = getScoreLabel(score);

  const isLg = size === "lg";
  const dim = isLg ? 96 : 40;
  const strokeWidth = isLg ? 6 : 3;
  const radius = (dim - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  // Compteurs de red flags non résolus
  const unresolvedCritical = insights.filter(
    (f) => f.status === "pending" && f.severity === "critical",
  ).length;
  const unresolvedHigh = insights.filter(
    (f) => f.status === "pending" && f.severity === "high",
  ).length;
  const totalUnresolved = unresolvedCritical + unresolvedHigh;
  const treatedCount = insights.filter(
    (f) => f.status === "confirmed" || f.status === "rejected",
  ).length;

  if (size === "sm") {
    return (
      <div className="flex items-center gap-1.5" title={`Workspace Score: ${score}/100`}>
        <svg width={dim} height={dim} className="shrink-0">
          <circle
            cx={dim / 2}
            cy={dim / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            className="text-vault-border"
          />
          <circle
            cx={dim / 2}
            cy={dim / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className={cn(colors.ring, "transition-all duration-700")}
            transform={`rotate(-90 ${dim / 2} ${dim / 2})`}
          />
          <text
            x={dim / 2}
            y={dim / 2}
            textAnchor="middle"
            dominantBaseline="central"
            className="fill-vault-text text-[11px] font-mono font-bold"
          >
            {score}
          </text>
        </svg>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-4">
      {/* Cercle SVG */}
      <svg width={dim} height={dim} className="shrink-0">
        <circle
          cx={dim / 2}
          cy={dim / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-vault-border"
        />
        <circle
          cx={dim / 2}
          cy={dim / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className={cn(colors.ring, "transition-all duration-700")}
          transform={`rotate(-90 ${dim / 2} ${dim / 2})`}
        />
        <text
          x={dim / 2}
          y={dim / 2}
          textAnchor="middle"
          dominantBaseline="central"
          className="fill-vault-text text-lg font-mono font-bold"
        >
          {score}
        </text>
      </svg>

      {/* Détails texte */}
      <div className="flex flex-col gap-0.5">
        <span className="text-[15px] font-semibold text-vault-text">
          Workspace Score — {label}
        </span>
        {totalUnresolved > 0 && (
          <span className="text-[12px] text-vault-text-muted">
            {totalUnresolved} alerte{totalUnresolved > 1 ? "s" : ""} non résolue{totalUnresolved > 1 ? "s" : ""}
          </span>
        )}
        {insights.length > 0 && (
          <span className="text-[12px] text-vault-text-muted">
            {treatedCount} point{treatedCount > 1 ? "s" : ""} clé{treatedCount > 1 ? "s" : ""} traité{treatedCount > 1 ? "s" : ""} sur {insights.length}
          </span>
        )}
      </div>
    </div>
  );
}
