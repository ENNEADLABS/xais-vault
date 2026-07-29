import { vi } from "vitest";
import type { UseQueryResult } from "@tanstack/react-query";

/**
 * Propriétés de base partagées entre tous les états de UseQueryResult.
 * Évite les casts `as unknown as` dans les tests.
 */
const BASE_RESULT = {
  dataUpdatedAt: 0,
  errorUpdatedAt: 0,
  failureCount: 0,
  failureReason: null,
  errorUpdateCount: 0,
  isFetched: false,
  isFetchedAfterMount: false,
  isInitialLoading: false,
  isPaused: false,
  isPlaceholderData: false,
  isRefetchError: false,
  isRefetching: false,
  isStale: false,
  isEnabled: true,
  refetch: vi.fn(),
} as const;

/** Mock UseQueryResult en état loading */
export function mockQueryLoading<TData>(): UseQueryResult<TData, Error> {
  return {
    ...BASE_RESULT,
    data: undefined,
    error: null,
    isError: false,
    isFetching: true,
    isLoading: true,
    isPending: true,
    isLoadingError: false,
    isSuccess: false,
    status: "pending",
    fetchStatus: "fetching",
    promise: Promise.resolve() as Promise<TData>,
  } as UseQueryResult<TData, Error>;
}

/** Mock UseQueryResult en état succès avec données */
export function mockQuerySuccess<TData>(data: TData): UseQueryResult<TData, Error> {
  return {
    ...BASE_RESULT,
    data,
    error: null,
    isError: false,
    isFetched: true,
    isFetchedAfterMount: true,
    isFetching: false,
    isLoading: false,
    isPending: false,
    isLoadingError: false,
    isSuccess: true,
    status: "success",
    fetchStatus: "idle",
    promise: Promise.resolve(data) as Promise<TData>,
  } as UseQueryResult<TData, Error>;
}

/** Mock UseQueryResult en état erreur */
export function mockQueryError<TData>(error?: Error): UseQueryResult<TData, Error> {
  return {
    ...BASE_RESULT,
    data: undefined,
    error: error ?? new Error("Test error"),
    isError: true,
    isFetched: true,
    isFetchedAfterMount: true,
    isFetching: false,
    isLoading: false,
    isPending: false,
    isLoadingError: true,
    isSuccess: false,
    status: "error",
    fetchStatus: "idle",
    promise: Promise.resolve() as Promise<TData>,
  } as UseQueryResult<TData, Error>;
}
