import { useState, useCallback, type DragEvent } from "react";

interface UseDragDropOptions {
  onFiles: (files: File[]) => void;
}

interface UseDragDropReturn {
  isDragging: boolean;
  dragHandlers: {
    onDragEnter: (e: DragEvent) => void;
    onDragLeave: (e: DragEvent) => void;
    onDragOver: (e: DragEvent) => void;
    onDrop: (e: DragEvent) => void;
  };
}

/**
 * Hook pour gérer le drag & drop de fichiers sur un container.
 * Gère le isDragging avec protection contre les faux dragLeave sur les enfants.
 */
export function useDragDrop({ onFiles }: UseDragDropOptions): UseDragDropReturn {
  const [isDragging, setIsDragging] = useState(false);

  const onDragEnter = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Ne quitter le mode drag que si on sort vraiment du container
    const rect = e.currentTarget.getBoundingClientRect();
    const { clientX, clientY } = e;
    if (
      clientX < rect.left ||
      clientX > rect.right ||
      clientY < rect.top ||
      clientY > rect.bottom
    ) {
      setIsDragging(false);
    }
  }, []);

  const onDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const onDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      if (e.dataTransfer.files.length > 0) {
        onFiles(Array.from(e.dataTransfer.files));
      }
    },
    [onFiles],
  );

  return {
    isDragging,
    dragHandlers: { onDragEnter, onDragLeave, onDragOver, onDrop },
  };
}
