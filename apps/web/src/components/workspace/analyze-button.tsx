"use client";

import { useTranslations } from "next-intl";
import {
  Scan,
  ChevronDown,
  Zap,
  Search,
  Microscope,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useLaunchScan } from "@/lib/hooks/use-launch-scan";

type ScanMode = "quick" | "standard" | "deep";

interface AnalyzeButtonProps {
  workspaceId: string;
  scanStatus: string;
}

const MODES: {
  value: ScanMode;
  icon: React.ElementType;
  labelKey: string;
  descKey: string;
}[] = [
  {
    value: "quick",
    icon: Zap,
    labelKey: "modeQuick",
    descKey: "modeQuickDesc",
  },
  {
    value: "standard",
    icon: Search,
    labelKey: "modeStandard",
    descKey: "modeStandardDesc",
  },
  {
    value: "deep",
    icon: Microscope,
    labelKey: "modeDeep",
    descKey: "modeDeepDesc",
  },
];

export function AnalyzeButton({ workspaceId, scanStatus }: AnalyzeButtonProps) {
  const t = useTranslations("studio.ddLaunch");
  const launchScan = useLaunchScan(workspaceId);
  const isScanning = scanStatus === "scanning";
  const disabled = isScanning || launchScan.isPending;

  function handleLaunch(mode: ScanMode) {
    launchScan.mutate(mode, {
      onSuccess: () =>
        toast.success(
          t("launched", {
            mode: t(
              `mode${mode.charAt(0).toUpperCase() + mode.slice(1)}` as Parameters<
                typeof t
              >[0],
            ),
          }),
        ),
    });
  }

  return (
    <div className="flex items-center">
      <Button
        size="sm"
        className="h-7 gap-1.5 rounded-r-none text-xs"
        onClick={() => handleLaunch("standard")}
        disabled={disabled}
      >
        {disabled ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Scan className="h-3.5 w-3.5" />
        )}
        {isScanning ? t("scanning") : t("launch")}
      </Button>

      <DropdownMenu>
        <DropdownMenuTrigger
          className="inline-flex h-7 items-center rounded-r-md rounded-l-none border-l border-white/20 bg-primary px-1.5 text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          disabled={disabled}
        >
          <ChevronDown className="h-3.5 w-3.5" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          {MODES.map(({ value, icon: Icon, labelKey, descKey }) => (
            <DropdownMenuItem
              key={value}
              onClick={() => handleLaunch(value)}
              className="flex items-start gap-2 py-2"
            >
              <Icon
                className={cn(
                  "h-4 w-4 mt-0.5 shrink-0",
                  value === "deep" && "text-purple-400",
                )}
              />
              <div>
                <p className="text-xs font-medium">
                  {t(labelKey as Parameters<typeof t>[0])}
                </p>
                <p className="text-[11px] text-vault-text-muted">
                  {t(descKey as Parameters<typeof t>[0])}
                </p>
              </div>
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
