"use client";

import { useEffect, useEffectEvent } from "react";
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
  const handleEvent = useEffectEvent(onEvent);
  const eventKey = events.join(",");

  useEffect(() => {
    if (!enabled) return;

    const supabase = createClient();
    const channelName = `realtime:${table}:${filter ?? "all"}`;

    let channel: RealtimeChannel = supabase.channel(channelName);

    for (const event of eventKey.split(",") as PostgresEvent[]) {
      channel = channel.on(
        "postgres_changes",
        {
          event,
          schema: "public",
          table,
          ...(filter ? { filter } : {}),
        },
        () => {
          handleEvent();
        },
      );
    }

    channel.subscribe();

    return () => {
      void supabase.removeChannel(channel);
    };
  }, [table, filter, enabled, eventKey]);
}
