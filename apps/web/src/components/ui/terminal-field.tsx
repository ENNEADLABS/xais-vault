import { forwardRef } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

interface TerminalFieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  id: string;
  label: string;
  error?: string;
}

export const TerminalField = forwardRef<HTMLInputElement, TerminalFieldProps>(
  function TerminalField({ id, label, error, className, ...props }, ref) {
    return (
      <div className={cn("space-y-2", className)}>
        <Label
          htmlFor={id}
          className="font-mono text-xs tracking-[0.15em] text-vault-text-secondary uppercase"
        >
          {label}
        </Label>
        <Input
          id={id}
          ref={ref}
          className={cn(
            "rounded-none border-0 border-b border-vault-border bg-transparent px-0",
            "text-vault-text placeholder:text-vault-text-secondary/40",
            "focus-visible:ring-0 focus-visible:border-vault-accent",
            "transition-colors duration-200",
            "h-10",
            error && "border-vault-danger",
          )}
          {...props}
        />
        {error && <p className="text-xs text-vault-danger">{error}</p>}
      </div>
    );
  },
);

export default TerminalField;
