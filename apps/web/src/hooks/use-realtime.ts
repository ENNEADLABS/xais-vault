"use client";

import { useEffect, useRef } from "react";
import { createClient } from "@/lib/supabase/client";
import type { RealtimeChannel } from "@supabase/supabase-js";

type PostgresEvent = "INSERT" | "UPDATE" | "DELETE" | "*";

interface UseRealtimeOptions {
  /** Nom de la table Supabase à écouter */
  table: string;
  /** Filtre au format "column=eq.value" */
  filter?: string;
  /** Types d'événements à écouter (défaut: tous) */
  events?: PostgresEvent[];
  /** Callback appelé quand un changement est détecté */
  onEvent: () => void;
  /** Désactiver la souscription (ex: si workspaceId est undefined) */
  enabled?: boolean;
}

export function useRealtime({
  table,
  filter,
  events = ["*"],
  onEvent,
  enabled = true,
}: UseRealtimeOptions) {
  // Ref stable pour le callback — évite les re-subscribe inutiles
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!enabled) return;

    const supabase = createClient();
    const channelName = `realtime:${table}:${filter ?? "all"}`;

    let channel: RealtimeChannel = supabase.channel(channelName);

    for (const event of events) {
      channel = channel.on(
        "postgres_changes",
        {
          event,
          schema: "public",
          table,
          ...(filter ? { filter } : {}),
        },
        () => {
          onEventRef.current();
        },
      );
    }

    channel.subscribe();

    return () => {
      void supabase.removeChannel(channel);
    };
  }, [table, filter, enabled, events.join(",")]); // eslint-disable-line react-hooks/exhaustive-deps
}
