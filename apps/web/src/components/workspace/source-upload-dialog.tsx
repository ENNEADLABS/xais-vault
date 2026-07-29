"use client";

import { useRef, useState, useCallback, useEffect, type DragEvent, type ChangeEvent } from "react";
import { useTranslations } from "next-intl";
import { Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useUploadSource } from "@/lib/hooks/use-sources";
import { UploadFileList, type FileItem } from "./upload-file-list";
import { cn } from "@/lib/utils";

const ACCEPTED = ".pdf,.docx,.xlsx,.pptx,.txt,.md,.csv";
const MAX_CONCURRENT = 3;

interface SourceUploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  /** Fichiers pré-remplis (ex: drag & drop depuis le panneau sources) */
  initialFiles?: File[];
}

export function SourceUploadDialog({
  open,
  onOpenChange,
  workspaceId,
  initialFiles,
}: SourceUploadDialogProps) {
  const t = useTranslations("workspace_page");
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const { mutateAsync } = useUploadSource(workspaceId);

  // Injecter les fichiers pré-remplis à l'ouverture du dialog
  useEffect(() => {
    if (open && initialFiles && initialFiles.length > 0) {
      addFiles(initialFiles);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const isUploading = files.some((f) => f.status === "uploading");
  const allDone = files.length > 0 && files.every((f) => f.status === "success" || f.status === "error");

  function addFiles(newFiles: FileList | File[]) {
    const items: FileItem[] = Array.from(newFiles).map((file) => ({
      id: `${file.name}-${Date.now()}-${Math.random()}`,
      file,
      status: "pending" as const,
    }));
    setFiles((prev) => [...prev, ...items]);
  }

  function removeFile(id: string) {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  }

  function updateFile(id: string, update: Partial<FileItem>) {
    setFiles((prev) =>
      prev.map((f) => (f.id === id ? { ...f, ...update } : f)),
    );
  }

  const uploadAll = useCallback(async () => {
    const pending = files.filter((f) => f.status === "pending");
    for (let i = 0; i < pending.length; i += MAX_CONCURRENT) {
      const batch = pending.slice(i, i + MAX_CONCURRENT);
      await Promise.all(
        batch.map(async (item) => {
          updateFile(item.id, { status: "uploading" });
          try {
            await mutateAsync(item.file);
            updateFile(item.id, { status: "success" });
          } catch {
            updateFile(item.id, { status: "error", error: t("uploadError") });
          }
        }),
      );
    }
  }, [files, mutateAsync, t]);

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length > 0) addFiles(e.dataTransfer.files);
  }

  function handleFileInput(e: ChangeEvent<HTMLInputElement>) {
    if (!e.target.files || e.target.files.length === 0) return;
    addFiles(e.target.files);
    e.target.value = "";
  }

  function handleClose(v: boolean) {
    if (!v) { setFiles([]); setIsDragging(false); }
    onOpenChange(v);
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{t("uploadTitle")}</DialogTitle>
        </DialogHeader>

        {/* Zone de drop */}
        <div
          className={cn(
            "flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors",
            isDragging
              ? "border-vault-accent bg-vault-accent/5"
              : "border-vault-border hover:border-vault-text-muted/50",
          )}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragEnter={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
        >
          <Upload className="mb-3 h-8 w-8 text-vault-text-muted" />
          <p className="text-center text-sm text-vault-text-muted">
            {isDragging ? t("uploadDrop") : t("uploadDescription")}
          </p>
          <p className="mt-1 text-center text-xs text-vault-text-muted/60">
            PDF, DOCX, XLSX, PPTX, TXT, MD, CSV
          </p>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED}
            multiple
            className="hidden"
            onChange={handleFileInput}
          />
        </div>

        <UploadFileList files={files} onRemove={removeFile} />

        {/* Actions */}
        <div className="flex justify-end gap-2">
          {files.length > 0 && !allDone && (
            <Button
              onClick={(e) => { e.stopPropagation(); void uploadAll(); }}
              disabled={isUploading || files.every((f) => f.status !== "pending")}
              className="bg-vault-accent text-black hover:bg-vault-accent/90"
            >
              {isUploading ? t("uploading") : t("uploadButton")}
            </Button>
          )}
          {allDone && (
            <Button variant="outline" onClick={() => handleClose(false)}>
              {t("uploadDone")}
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
