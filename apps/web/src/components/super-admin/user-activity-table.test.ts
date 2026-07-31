import { describe, expect, it } from "vitest";
import { getActivityClass } from "./user-activity-table";

describe("getActivityClass", () => {
  const now = new Date("2026-07-31T12:00:00Z").getTime();

  it("marks activity from the last day as fresh", () => {
    expect(getActivityClass("2026-07-30T13:00:00Z", now)).toBe("text-green-400");
  });

  it("marks activity from the last week as recent", () => {
    expect(getActivityClass("2026-07-25T12:00:00Z", now)).toBe(
      "text-vault-text-secondary",
    );
  });

  it("marks missing or old activity as muted", () => {
    expect(getActivityClass(null, now)).toBe("text-vault-text-muted");
    expect(getActivityClass("2026-07-20T12:00:00Z", now)).toBe(
      "text-vault-text-muted",
    );
  });
});
