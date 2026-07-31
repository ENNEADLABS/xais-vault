import { useState, useMemo } from "react";
import type { Source } from "@/types/api";

interface UseMentionDropdownOptions {
  sources: Source[];
}

interface UseMentionDropdownReturn {
  showMention: boolean;
  mentionIndex: number;
  filteredSources: Source[];
  /** Met à jour la valeur et détecte les mentions @ */
  handleMentionDetection: (newValue: string) => void;
  /** Sélectionne une source et retourne la nouvelle valeur du textarea */
  selectMention: (source: Source, currentValue: string) => string;
  /** Gère les touches clavier dans le dropdown (retourne true si consommé) */
  handleMentionKeyDown: (key: string, shiftKey: boolean, metaKey: boolean, ctrlKey: boolean) => boolean;
  setMentionIndex: (index: number) => void;
  closeMention: () => void;
}

/**
 * Hook pour le dropdown de mention @source dans le chat input.
 * Gère la détection du @, le filtrage, la navigation clavier et la sélection.
 */
export function useMentionDropdown({
  sources,
}: UseMentionDropdownOptions): UseMentionDropdownReturn {
  const [showMention, setShowMention] = useState(false);
  const [mentionFilter, setMentionFilter] = useState("");
  const [mentionIndex, setMentionIndex] = useState(0);

  // Sources filtrées pour le dropdown
  const readySources = useMemo(
    () => sources.filter((s) => s.status === "ready"),
    [sources],
  );

  const filteredSources = useMemo(() => {
    if (!mentionFilter) return readySources;
    const lower = mentionFilter.toLowerCase();
    return readySources.filter((s) => s.name.toLowerCase().includes(lower));
  }, [readySources, mentionFilter]);

  function handleMentionDetection(newValue: string) {
    const lastAt = newValue.lastIndexOf("@");
    if (lastAt >= 0) {
      const afterAt = newValue.slice(lastAt + 1);
      if (!afterAt.includes(" ") && !afterAt.includes("\n")) {
        setShowMention(true);
        setMentionIndex(0);
        setMentionFilter(afterAt);
        return;
      }
    }
    setShowMention(false);
  }

  function selectMention(source: Source, currentValue: string): string {
    const lastAt = currentValue.lastIndexOf("@");
    const before = currentValue.slice(0, lastAt);
    setShowMention(false);
    return `${before}@${source.name} `;
  }

  function handleMentionKeyDown(
    key: string,
    shiftKey: boolean,
    metaKey: boolean,
    ctrlKey: boolean,
  ): boolean {
    if (!showMention || filteredSources.length === 0) return false;

    if (key === "ArrowDown") {
      setMentionIndex((i) => Math.min(i + 1, filteredSources.length - 1));
      return true;
    }
    if (key === "ArrowUp") {
      setMentionIndex((i) => Math.max(i - 1, 0));
      return true;
    }
    if (key === "Enter" && !shiftKey && !metaKey && !ctrlKey) {
      return true; // Consommé — l'appelant doit appeler selectMention
    }
    if (key === "Escape") {
      setShowMention(false);
      return true;
    }
    return false;
  }

  function closeMention() {
    setShowMention(false);
  }

  return {
    showMention,
    mentionIndex,
    filteredSources,
    handleMentionDetection,
    selectMention,
    handleMentionKeyDown,
    setMentionIndex,
    closeMention,
  };
}
