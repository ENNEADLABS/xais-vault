"use client";

import { useEffect, useRef, useCallback } from "react";

/**
 * Hook pour déclencher l'animation fade-up quand un élément entre dans le viewport.
 * Ajoute la classe `visible` sur l'élément observé.
 */
export function useFadeUp(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry?.isIntersecting) {
          el.classList.add("visible");
          observer.unobserve(el);
        }
      },
      { threshold },
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [threshold]);

  return [ref] as const;
}

/**
 * Callback ref pour observer plusieurs enfants d'un conteneur (stagger).
 * Utilisation : <div ref={staggerRef}> ... <div className="fade-up stagger-1"> ...
 */
export function useFadeUpChildren(threshold = 0.1) {
  const observerRef = useRef<IntersectionObserver | null>(null);

  const containerRef = useCallback(
    (node: HTMLDivElement | null) => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }

      if (!node) return;

      observerRef.current = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (entry.isIntersecting) {
              entry.target.classList.add("visible");
              observerRef.current?.unobserve(entry.target);
            }
          }
        },
        { threshold },
      );

      const children = node.querySelectorAll(".fade-up");
      for (const child of children) {
        observerRef.current.observe(child);
      }
    },
    [threshold],
  );

  return [containerRef] as const;
}
