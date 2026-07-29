import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";

// Mocks Supabase auth
const mockSignInWithPassword = vi.fn();
const mockSignInWithOtp = vi.fn();

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: {
      signInWithPassword: mockSignInWithPassword,
      signInWithOtp: mockSignInWithOtp,
    },
  }),
}));

// Mocks router
const mockPush = vi.fn();
const mockRefresh = vi.fn();

vi.mock("@/i18n/navigation", () => ({
  useRouter: () => ({ push: mockPush, refresh: mockRefresh }),
}));

import { useLoginForm } from "./use-login-form";

describe("useLoginForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // --- État initial ---

  it("démarre en mode password", () => {
    const { result } = renderHook(() => useLoginForm());
    expect(result.current.mode).toBe("password");
  });

  it("démarre sans erreur ni loading", () => {
    const { result } = renderHook(() => useLoginForm());
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.magicLinkSent).toBe(false);
  });

  it("expose les deux formulaires RHF", () => {
    const { result } = renderHook(() => useLoginForm());
    expect(result.current.passwordForm).toBeDefined();
    expect(result.current.magicLinkForm).toBeDefined();
    expect(result.current.passwordForm.getValues()).toEqual({ email: "", password: "" });
    expect(result.current.magicLinkForm.getValues()).toEqual({ email: "" });
  });

  // --- Changement de mode ---

  it("permet de basculer en mode magic-link", () => {
    const { result } = renderHook(() => useLoginForm());
    act(() => result.current.setMode("magic-link"));
    expect(result.current.mode).toBe("magic-link");
  });

  // --- Login par mot de passe ---

  it("redirige vers /workspaces après login password réussi", async () => {
    mockSignInWithPassword.mockResolvedValue({ error: null });

    const { result } = renderHook(() => useLoginForm());

    await act(async () => {
      await result.current.handlePasswordLogin({ email: "x@test.com", password: "secret123" });
    });

    expect(mockSignInWithPassword).toHaveBeenCalledWith({
      email: "x@test.com",
      password: "secret123",
    });
    expect(mockPush).toHaveBeenCalledWith("/workspaces");
    expect(mockRefresh).toHaveBeenCalled();
  });

  it("affiche l'erreur si login password échoue", async () => {
    mockSignInWithPassword.mockResolvedValue({
      error: { message: "Invalid login credentials" },
    });

    const { result } = renderHook(() => useLoginForm());

    await act(async () => {
      await result.current.handlePasswordLogin({ email: "x@test.com", password: "wrong" });
    });

    expect(result.current.error).toBe("Invalid login credentials");
    expect(result.current.loading).toBe(false);
    expect(mockPush).not.toHaveBeenCalled();
  });

  // --- Magic link ---

  it("envoie le magic link et marque magicLinkSent", async () => {
    mockSignInWithOtp.mockResolvedValue({ error: null });

    const { result } = renderHook(() => useLoginForm());

    await act(async () => {
      await result.current.handleMagicLink({ email: "x@test.com" });
    });

    expect(mockSignInWithOtp).toHaveBeenCalledWith({
      email: "x@test.com",
      options: { emailRedirectTo: expect.stringContaining("/callback") },
    });
    expect(result.current.magicLinkSent).toBe(true);
    expect(result.current.loading).toBe(false);
  });

  it("affiche l'erreur si magic link échoue", async () => {
    mockSignInWithOtp.mockResolvedValue({
      error: { message: "Rate limit exceeded" },
    });

    const { result } = renderHook(() => useLoginForm());

    await act(async () => {
      await result.current.handleMagicLink({ email: "x@test.com" });
    });

    expect(result.current.error).toBe("Rate limit exceeded");
    expect(result.current.loading).toBe(false);
    expect(result.current.magicLinkSent).toBe(false);
  });

  // --- Validation Zod ---

  it("rejette un email invalide sur passwordForm", async () => {
    const { result } = renderHook(() => useLoginForm());

    let valid = true;
    await act(async () => {
      result.current.passwordForm.setValue("email", "not-an-email");
      result.current.passwordForm.setValue("password", "secret123");
      valid = await result.current.passwordForm.trigger();
    });

    expect(valid).toBe(false);
  });

  it("rejette un mot de passe trop court sur passwordForm", async () => {
    const { result } = renderHook(() => useLoginForm());

    let valid = true;
    await act(async () => {
      result.current.passwordForm.setValue("email", "x@test.com");
      result.current.passwordForm.setValue("password", "123");
      valid = await result.current.passwordForm.trigger();
    });

    expect(valid).toBe(false);
  });

  it("rejette un email invalide sur magicLinkForm", async () => {
    const { result } = renderHook(() => useLoginForm());

    let valid = true;
    await act(async () => {
      result.current.magicLinkForm.setValue("email", "bad");
      valid = await result.current.magicLinkForm.trigger();
    });

    expect(valid).toBe(false);
  });

  it("passe la validation avec des données valides", async () => {
    const { result } = renderHook(() => useLoginForm());

    await act(async () => {
      result.current.passwordForm.setValue("email", "x@test.com");
      result.current.passwordForm.setValue("password", "secret123");
      await result.current.passwordForm.trigger();
    });

    expect(result.current.passwordForm.formState.errors.email).toBeUndefined();
    expect(result.current.passwordForm.formState.errors.password).toBeUndefined();
  });
});
