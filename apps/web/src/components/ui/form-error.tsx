interface FormErrorProps {
  message: string | null | undefined;
  className?: string;
}

export function FormError({ message, className }: FormErrorProps) {
  if (!message) return null;
  return (
    <p className={`text-sm text-destructive ${className ?? ""}`}>{message}</p>
  );
}
