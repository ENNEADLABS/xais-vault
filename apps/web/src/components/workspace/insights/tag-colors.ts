/**
 * Couleurs sémantiques pour les tags de notes.
 * Les tags preset ont des couleurs distinctes, les custom ont un style neutre.
 */

const TAG_COLORS: Record<string, string> = {
  action: "bg-blue-500/15 text-blue-400",
  risque: "bg-red-500/15 text-red-400",
  verified: "bg-green-500/15 text-green-400",
  question: "bg-amber-500/15 text-amber-400",
};

const DEFAULT_TAG_COLOR = "bg-vault-border/30 text-vault-text-secondary";

export const PRESET_TAGS = [
  { label: "action", color: TAG_COLORS.action },
  { label: "risque", color: TAG_COLORS.risque },
  { label: "verified", color: TAG_COLORS.verified },
  { label: "question", color: TAG_COLORS.question },
] as const;

export function getTagColor(tag: string): string {
  const normalized = tag.replace(/^#/, "").toLowerCase();
  return TAG_COLORS[normalized] ?? DEFAULT_TAG_COLOR;
}
