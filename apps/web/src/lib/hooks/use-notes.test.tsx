import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();
const mockDelete = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
    patch: (...args: unknown[]) => mockPatch(...args),
    delete: (...args: unknown[]) => mockDelete(...args),
    setOrganizationId: vi.fn(),
  },
}));

import { useNotes, useCreateNote, useUpdateNote, useDeleteNote } from "./use-notes";

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

const NOTE = { id: "n-1", content: "Note test", title: "Titre", tags: [], is_pinned: false };

describe("useNotes", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue({ data: [NOTE] });
  });

  it("appelle GET /workspaces/:id/notes/", async () => {
    const { result } = renderHook(() => useNotes("d-1"), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/workspaces/d-1/notes/");
  });

  it("n'appelle pas l'API si workspaceId est vide", () => {
    renderHook(() => useNotes(""), { wrapper: createWrapper() });
    expect(mockGet).not.toHaveBeenCalled();
  });
});

describe("useCreateNote", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPost.mockResolvedValue({ data: NOTE });
  });

  it("appelle POST /workspaces/:id/notes/ avec le contenu", async () => {
    const { result } = renderHook(() => useCreateNote("d-1"), { wrapper: createWrapper() });
    result.current.mutate({ content: "Note test", title: "Titre" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPost).toHaveBeenCalledWith("/workspaces/d-1/notes/", {
      content: "Note test",
      title: "Titre",
    });
  });

  it("accepte les champs optionnels", async () => {
    const { result } = renderHook(() => useCreateNote("d-1"), { wrapper: createWrapper() });
    result.current.mutate({
      content: "Note épinglée",
      is_pinned: true,
      tags: ["important"],
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPost).toHaveBeenCalledWith("/workspaces/d-1/notes/", expect.objectContaining({
      is_pinned: true,
      tags: ["important"],
    }));
  });
});

describe("useUpdateNote", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPatch.mockResolvedValue({ data: { ...NOTE, is_pinned: true } });
  });

  it("appelle PATCH /workspaces/:id/notes/:noteId", async () => {
    const { result } = renderHook(() => useUpdateNote("d-1"), { wrapper: createWrapper() });
    result.current.mutate({ noteId: "n-1", update: { is_pinned: true } });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPatch).toHaveBeenCalledWith("/workspaces/d-1/notes/n-1", { is_pinned: true });
  });
});

describe("useDeleteNote", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockDelete.mockResolvedValue({});
  });

  it("appelle DELETE /workspaces/:id/notes/:noteId", async () => {
    const { result } = renderHook(() => useDeleteNote("d-1"), { wrapper: createWrapper() });
    result.current.mutate("n-1");
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockDelete).toHaveBeenCalledWith("/workspaces/d-1/notes/n-1");
  });
});
