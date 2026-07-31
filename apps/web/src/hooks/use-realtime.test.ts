import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const channelOn = vi.fn();
const subscribe = vi.fn();
const removeChannel = vi.fn();
const channel = { on: channelOn, subscribe };

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    channel: vi.fn(() => channel),
    removeChannel,
  }),
}));

import { useRealtime } from "./use-realtime";

describe("useRealtime", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    channelOn.mockReturnValue(channel);
  });

  it("uses the latest callback without resubscribing", () => {
    const firstCallback = vi.fn();
    const secondCallback = vi.fn();
    const { rerender } = renderHook(
      ({ onEvent }) =>
        useRealtime({ table: "sources", events: ["UPDATE"], onEvent }),
      { initialProps: { onEvent: firstCallback } },
    );

    const postgresHandler = channelOn.mock.calls[0][2] as () => void;
    rerender({ onEvent: secondCallback });

    act(() => postgresHandler());

    expect(firstCallback).not.toHaveBeenCalled();
    expect(secondCallback).toHaveBeenCalledOnce();
    expect(channelOn).toHaveBeenCalledOnce();
  });
});
