import type { Insight, Investigation } from "@/types/api";

export const SEVERITY_CLASSES: Record<Insight["severity"], string> = {
  critical: "bg-vault-danger-dim text-vault-danger",
  high: "bg-vault-warning-dim text-vault-warning",
  medium: "bg-vault-medium-dim text-vault-medium",
  low: "bg-vault-low-dim text-vault-low",
};

export const FINDING_STATUS_CLASSES: Record<Insight["status"], string> = {
  pending: "bg-vault-medium-dim text-vault-medium",
  confirmed: "bg-vault-success-dim text-vault-success",
  rejected: "bg-vault-low-dim text-vault-text-secondary line-through",
  investigating: "bg-vault-accent-dim text-vault-accent",
};

export const INVESTIGATION_STATUS_CLASSES: Record<
  Investigation["status"],
  string
> = {
  pending: "bg-vault-medium-dim text-vault-medium",
  processing: "bg-vault-accent-dim text-vault-accent animate-pulse",
  completed: "bg-vault-success-dim text-vault-success",
  failed: "bg-vault-danger-dim text-vault-danger",
};
