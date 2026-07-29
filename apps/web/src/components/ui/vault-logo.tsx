import { cn } from "@/lib/utils";

interface VaultLogoProps {
  size?: "sm" | "md" | "lg" | "xl";
  showText?: boolean;
  className?: string;
}

const sizeMap = {
  sm: { icon: 20, text: "text-[11px]", gap: "gap-1.5" },
  md: { icon: 24, text: "text-[13px]", gap: "gap-2" },
  lg: { icon: 32, text: "text-lg", gap: "gap-2.5" },
  xl: { icon: 48, text: "text-3xl", gap: "gap-3" },
};

/**
 * Logo XAIS VAULT — icône shield géométrique + texte.
 * Utilise les tokens CSS vault pour s'adapter au thème.
 */
export function VaultLogo({ size = "md", showText = true, className }: VaultLogoProps) {
  const s = sizeMap[size];

  return (
    <span className={cn("inline-flex items-center", s.gap, className)}>
      <svg
        width={s.icon}
        height={s.icon}
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        {/* Shield / hexagone */}
        <path
          d="M16 2L28 8V18C28 24 22.5 29 16 30C9.5 29 4 24 4 18V8L16 2Z"
          className="stroke-vault-accent"
          strokeWidth="1.5"
          fill="none"
        />
        {/* Lignes internes — motif coffre-fort */}
        <path
          d="M16 8V24"
          className="stroke-vault-accent"
          strokeWidth="1"
          opacity="0.5"
        />
        <path
          d="M10 12H22"
          className="stroke-vault-accent"
          strokeWidth="1"
          opacity="0.5"
        />
        <path
          d="M10 20H22"
          className="stroke-vault-accent"
          strokeWidth="1"
          opacity="0.5"
        />
        {/* Point central — serrure */}
        <circle
          cx="16"
          cy="16"
          r="2.5"
          className="fill-vault-accent"
          opacity="0.9"
        />
      </svg>
      {showText && (
        <span className={cn("font-mono font-semibold tracking-widest uppercase", s.text)}>
          <span className="text-vault-text">XAIS </span>
          <span className="text-vault-accent">VAULT</span>
        </span>
      )}
    </span>
  );
}
