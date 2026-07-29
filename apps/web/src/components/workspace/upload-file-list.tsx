"use client";

import { FileText, CheckCircle, AlertCircle, Upload, X } from "lucide-react";

type FileStatus = "pending" | "uploading" | "success" | "error";

export interface FileItem {
  id: string;
  file: File;
  status: FileStatus;
  error?: string;
}

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function StatusIcon({ status }: { status: FileStatus }) {
  switch (status) {
    case "pending":
      return <FileText className="h-4 w-4 shrink-0 text-vault-text-muted" />;
    case "uploading":
      return <Upload className="h-4 w-4 shrink-0 text-vault-accent animate-pulse" />;
    case "success":
      return <CheckCircle className="h-4 w-4 shrink-0 text-vault-success" />;
    case "error":
      return <AlertCircle className="h-4 w-4 shrink-0 text-vault-danger" />;
  }
}

interface UploadFileListProps {
  files: FileItem[];
  onRemove: (id: string) => void;
}

export function UploadFileList({ files, onRemove }: UploadFileListProps) {
  if (files.length === 0) return null;

  return (
    <div className="max-h-48 space-y-1 overflow-y-auto">
      {files.map((item) => (
        <div
          key={item.id}
          className="flex items-center gap-2 rounded px-2 py-1.5 text-sm"
        >
          <StatusIcon status={item.status} />
          <span className="flex-1 truncate text-vault-text-secondary">
            {item.file.name}
          </span>
          <span className="shrink-0 text-xs text-vault-text-muted">
            {formatSize(item.file.size)}
          </span>
          {item.status === "pending" && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onRemove(item.id); }}
              className="shrink-0 rounded p-0.5 text-vault-text-muted hover:text-vault-text"
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
