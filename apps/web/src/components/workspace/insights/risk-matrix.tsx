"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { Insight } from "@/types/api";

// ─── Constantes de positionnement ────────────────────────

const SEVERITY_Y: Record<Insight["severity"], number> = {
  low: 0.875,
  medium: 0.625,
  high: 0.375,
  critical: 0.125,
};

const SEVERITY_LABELS: { key: Insight["severity"]; label: string }[] = [
  { key: "critical", label: "Critique" },
  { key: "high", label: "Élevée" },
  { key: "medium", label: "Moyenne" },
  { key: "low", label: "Faible" },
];

const SEVERITY_COLORS: Record<Insight["severity"], string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#3b82f6",
};

// ─── Composant ───────────────────────────────────────────

interface RiskMatrixProps {
  insights: Insight[];
  onInsightClick?: (insightId: string) => void;
}

export function RiskMatrix({ insights, onInsightClick }: RiskMatrixProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  // Zone utile du SVG (padding pour labels)
  const W = 320;
  const H = 220;
  const PAD_L = 60;
  const PAD_R = 10;
  const PAD_T = 10;
  const PAD_B = 30;

  const plotW = W - PAD_L - PAD_R;
  const plotH = H - PAD_T - PAD_B;

  function toX(confidence: number) {
    return PAD_L + (confidence / 100) * plotW;
  }

  function toY(severity: Insight["severity"]) {
    return PAD_T + SEVERITY_Y[severity] * plotH;
  }

  const hoveredInsight = insights.find((f) => f.id === hoveredId);

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full h-auto"
        role="img"
        aria-label="Risk Matrix — insights par sévérité et confiance"
      >
        {/* Fond quadrants */}
        <rect
          x={PAD_L}
          y={PAD_T}
          width={plotW / 2}
          height={plotH / 2}
          fill="rgba(239, 68, 68, 0.04)"
        />
        <rect
          x={PAD_L + plotW / 2}
          y={PAD_T}
          width={plotW / 2}
          height={plotH / 2}
          fill="rgba(239, 68, 68, 0.08)"
        />
        <rect
          x={PAD_L}
          y={PAD_T + plotH / 2}
          width={plotW / 2}
          height={plotH / 2}
          fill="rgba(59, 130, 246, 0.03)"
        />
        <rect
          x={PAD_L + plotW / 2}
          y={PAD_T + plotH / 2}
          width={plotW / 2}
          height={plotH / 2}
          fill="rgba(59, 130, 246, 0.06)"
        />

        {/* Lignes de grille horizontales */}
        {SEVERITY_LABELS.map(({ key }) => (
          <line
            key={key}
            x1={PAD_L}
            x2={W - PAD_R}
            y1={toY(key)}
            y2={toY(key)}
            stroke="currentColor"
            strokeWidth={0.5}
            className="text-vault-border"
            strokeDasharray="3,3"
          />
        ))}

        {/* Labels axe Y (sévérité) */}
        {SEVERITY_LABELS.map(({ key, label }) => (
          <text
            key={key}
            x={PAD_L - 6}
            y={toY(key)}
            textAnchor="end"
            dominantBaseline="central"
            className="fill-vault-text-muted"
            fontSize={9}
          >
            {label}
          </text>
        ))}

        {/* Labels axe X (confiance) */}
        {[0, 25, 50, 75, 100].map((v) => (
          <text
            key={v}
            x={toX(v)}
            y={H - 6}
            textAnchor="middle"
            className="fill-vault-text-muted"
            fontSize={9}
          >
            {v}%
          </text>
        ))}

        {/* Titre axe X */}
        <text
          x={PAD_L + plotW / 2}
          y={H}
          textAnchor="middle"
          className="fill-vault-text-secondary"
          fontSize={9}
        >
          Confiance
        </text>

        {/* Points (insights) */}
        {insights.map((f) => {
          const cx = toX(f.confidence_score);
          const cy = toY(f.severity);
          const isHovered = hoveredId === f.id;
          return (
            <circle
              key={f.id}
              cx={cx}
              cy={cy}
              r={isHovered ? 7 : 5}
              fill={SEVERITY_COLORS[f.severity]}
              fillOpacity={f.status === "rejected" ? 0.3 : 0.85}
              stroke={isHovered ? "#fff" : "none"}
              strokeWidth={isHovered ? 1.5 : 0}
              className="cursor-pointer transition-all duration-150"
              onMouseEnter={() => setHoveredId(f.id)}
              onMouseLeave={() => setHoveredId(null)}
              onClick={() => onInsightClick?.(f.id)}
            />
          );
        })}
      </svg>

      {/* Tooltip */}
      {hoveredInsight && (
        <div className="absolute top-2 right-2 z-10 rounded-lg bg-vault-surface border border-vault-border p-2 shadow-lg max-w-[200px] pointer-events-none">
          <p className="text-[12px] font-medium text-vault-text leading-snug truncate">
            {hoveredInsight.title}
          </p>
          <div className="flex items-center gap-2 mt-1">
            <span
              className={cn(
                "rounded-full px-1.5 py-0.5 text-[10px] font-medium uppercase",
                hoveredInsight.severity === "critical" && "bg-vault-danger-dim text-vault-danger",
                hoveredInsight.severity === "high" && "bg-vault-warning-dim text-vault-warning",
                hoveredInsight.severity === "medium" && "bg-vault-medium-dim text-vault-medium",
                hoveredInsight.severity === "low" && "bg-vault-low-dim text-vault-low",
              )}
            >
              {hoveredInsight.severity}
            </span>
            <span className="text-[10px] text-vault-text-muted">
              {hoveredInsight.confidence_score}%
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
