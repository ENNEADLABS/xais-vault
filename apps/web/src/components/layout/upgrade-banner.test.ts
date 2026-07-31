import { describe, expect, it } from "vitest";
import { isTrialExpiringSoon } from "./upgrade-banner";

describe("isTrialExpiringSoon", () => {
  const now = new Date("2026-07-31T12:00:00Z").getTime();

  it("returns true when the trial ends within three days", () => {
    expect(isTrialExpiringSoon("2026-08-03T12:00:00Z", now)).toBe(true);
  });

  it("returns false when the trial has expired", () => {
    expect(isTrialExpiringSoon("2026-07-30T12:00:00Z", now)).toBe(false);
  });

  it("returns false when more than three days remain", () => {
    expect(isTrialExpiringSoon("2026-08-04T12:00:01Z", now)).toBe(false);
  });
});
