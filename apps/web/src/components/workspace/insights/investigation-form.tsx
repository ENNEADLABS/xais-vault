"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Search } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useCreateInvestigation } from "@/lib/hooks/use-investigations";

interface InvestigationFormProps {
  workspaceId: string;
  insightId: string;
  onSuccess?: () => void;
}

type Scope = "documents" | "web" | "both";

export function InvestigationForm({
  workspaceId,
  insightId,
  onSuccess,
}: InvestigationFormProps) {
  const t = useTranslations("insightDetail.investigation");
  const [question, setQuestion] = useState("");
  const [scope, setScope] = useState<Scope>("both");
  const createInvestigation = useCreateInvestigation(workspaceId);

  async function handleSubmit() {
    if (!question.trim()) return;
    createInvestigation.mutate(
      {
        question: question.trim(),
        insight_id: insightId,
        scope,
      },
      {
        onSuccess: () => {
          toast.success(t("launched"));
          setQuestion("");
          onSuccess?.();
        },
      },
    );
  }

  const scopes: { value: Scope; label: string }[] = [
    { value: "both", label: t("scopeBoth") },
    { value: "documents", label: t("scopeDocuments") },
    { value: "web", label: t("scopeWeb") },
  ];

  return (
    <div className="space-y-2.5">
      <textarea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder={t("questionPlaceholder")}
        maxLength={500}
        rows={2}
        className="w-full resize-none rounded-lg border border-vault-border bg-vault-bg px-3 py-2 text-[13px] placeholder:text-vault-text-muted/50 outline-none focus:border-vault-accent/50"
      />

      <div className="flex items-center gap-1.5">
        {scopes.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            onClick={() => setScope(value)}
            className={cn(
              "rounded-md px-2 py-1 text-[11px] font-mono transition-colors",
              scope === value
                ? "bg-vault-accent/15 text-vault-accent"
                : "bg-vault-border/20 text-vault-text-muted hover:bg-vault-border/40",
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <Button
        size="sm"
        className="h-7 gap-1.5 text-xs"
        onClick={handleSubmit}
        disabled={!question.trim() || createInvestigation.isPending}
      >
        <Search className="h-3.5 w-3.5" />
        {t("launch")}
      </Button>
    </div>
  );
}
