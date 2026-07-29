import {
  Briefcase,
  Building2,
  Landmark,
  CircleDollarSign,
  TrendingUp,
  BarChart3,
  Rocket,
  Zap,
  type LucideIcon,
} from "lucide-react";

export const ICON_MAP: Record<string, LucideIcon> = {
  briefcase: Briefcase,
  building2: Building2,
  landmark: Landmark,
  circledollarsign: CircleDollarSign,
  trendingup: TrendingUp,
  barchart3: BarChart3,
  rocket: Rocket,
  zap: Zap,
};

interface WorkspaceIconProps {
  emoji?: string | null;
  className?: string;
}

// Rend l'icône Lucide si c'est un identifiant connu, sinon affiche l'emoji brut (legacy)
export function WorkspaceIcon({ emoji, className = "h-4 w-4 text-vault-text-muted" }: WorkspaceIconProps) {
  if (!emoji) return <Briefcase className={className} />;

  const Icon = ICON_MAP[emoji];
  if (Icon) return <Icon className={className} />;

  // Emoji natif (valeurs legacy ou custom "😀")
  return <>{emoji}</>;
}
