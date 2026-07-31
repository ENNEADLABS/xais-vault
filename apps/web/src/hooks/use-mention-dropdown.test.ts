import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useMentionDropdown } from "./use-mention-dropdown";
import type { Source } from "@/types/api";

const SOURCES = [
  { id: "source-1", name: "Budget.pdf", status: "ready" },
  { id: "source-2", name: "Business plan.pdf", status: "ready" },
] as Source[];

describe("useMentionDropdown", () => {
  it("resets keyboard selection when the mention filter changes", () => {
    const { result } = renderHook(() =>
      useMentionDropdown({ sources: SOURCES }),
    );

    act(() => result.current.handleMentionDetection("@"));
    act(() => result.current.setMentionIndex(1));
    expect(result.current.mentionIndex).toBe(1);

    act(() => result.current.handleMentionDetection("@Bus"));
    expect(result.current.mentionIndex).toBe(0);
    expect(result.current.filteredSources).toHaveLength(1);
  });
});
