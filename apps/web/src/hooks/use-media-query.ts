import { useCallback, useSyncExternalStore } from "react";

export const BREAKPOINTS = {
  md: "(min-width: 768px)",
  lg: "(min-width: 1024px)",
} as const;

export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (cb: () => void) => {
      const mql = window.matchMedia(query);
      mql.addEventListener("change", cb);
      return () => mql.removeEventListener("change", cb);
    },
    [query],
  );

  return useSyncExternalStore(
    subscribe,
    () => window.matchMedia(query).matches,
    () => false,
  );
}
