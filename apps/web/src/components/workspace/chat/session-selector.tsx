"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  ChevronDown,
  Plus,
  MoreHorizontal,
  Pencil,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  useRenameSession,
  useDeleteSession,
} from "@/lib/hooks/use-chat-sessions";
import type { ChatSession } from "@/types/api";

interface SessionSelectorProps {
  workspaceId: string;
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelect: (id: string | null) => void;
}

export function SessionSelector({
  workspaceId,
  sessions,
  activeSessionId,
  onSelect,
}: SessionSelectorProps) {
  const t = useTranslations("chat");
  const activeSession = sessions.find((s) => s.id === activeSessionId);
  const [renameOpen, setRenameOpen] = useState(false);
  const [renameTarget, setRenameTarget] = useState<ChatSession | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const { mutate: rename } = useRenameSession(workspaceId);
  const { mutate: deleteSession } = useDeleteSession(workspaceId);

  function startRename(session: ChatSession) {
    setRenameTarget(session);
    setRenameValue(session.title ?? "");
    setRenameOpen(true);
  }

  function submitRename() {
    if (!renameTarget) return;
    rename({ sessionId: renameTarget.id, title: renameValue });
    setRenameOpen(false);
  }

  function handleDelete(session: ChatSession) {
    if (!confirm(t("deleteConfirm"))) return;
    deleteSession(session.id);
    if (activeSessionId === session.id) onSelect(null);
  }

  return (
    <>
      <div className="flex shrink-0 items-center border-b border-vault-border px-3 py-2.5">
        <DropdownMenu>
          <DropdownMenuTrigger className="flex h-7 max-w-[200px] items-center gap-1 rounded-md px-2 text-xs font-medium text-vault-text hover:bg-vault-surface-active">
            <span className="truncate">
              {activeSession?.title ?? t("newSession")}
            </span>
            <ChevronDown className="h-3 w-3 shrink-0" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-56">
            <DropdownMenuItem onClick={() => onSelect(null)}>
              <Plus className="mr-2 h-3.5 w-3.5" />
              {t("newSession")}
            </DropdownMenuItem>
            {sessions.length > 0 && <DropdownMenuSeparator />}
            {sessions.map((session) => (
              <DropdownMenuItem
                key={session.id}
                className="flex items-center justify-between"
                onClick={() => onSelect(session.id)}
              >
                <span className="truncate text-xs">
                  {session.title ?? t("newSession")}
                </span>
                <span
                  className="ml-2 shrink-0 opacity-50 hover:opacity-100"
                  onClick={(e) => {
                    e.stopPropagation();
                  }}
                >
                  <DropdownMenu>
                    <DropdownMenuTrigger className="inline-flex items-center justify-center rounded p-0.5 hover:bg-vault-surface-active">
                      <MoreHorizontal className="h-3.5 w-3.5" />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent>
                      <DropdownMenuItem onClick={() => startRename(session)}>
                        <Pencil className="mr-2 h-3.5 w-3.5" />
                        {t("rename")}
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        className="text-destructive"
                        onClick={() => handleDelete(session)}
                      >
                        <Trash2 className="mr-2 h-3.5 w-3.5" />
                        {t("delete")}
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </span>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <Dialog open={renameOpen} onOpenChange={setRenameOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>{t("renameTitle")}</DialogTitle>
          </DialogHeader>
          <div className="flex gap-2">
            <Input
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              placeholder={t("renamePlaceholder")}
              onKeyDown={(e) => e.key === "Enter" && submitRename()}
            />
            <Button onClick={submitRename}>{t("renameSubmit")}</Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
