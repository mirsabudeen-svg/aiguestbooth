"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { EventItem, getEvents, getToken } from "@/lib/api";

const STORAGE_KEY = "booth_selected_event_id";

interface EventContextValue {
  events: EventItem[];
  selectedEventId: string | null;
  selectedEvent: EventItem | null;
  setSelectedEventId: (id: string | null) => void;
  loading: boolean;
  refreshEvents: () => Promise<void>;
}

const EventContext = createContext<EventContextValue | null>(null);

export function EventProvider({ children }: { children: React.ReactNode }) {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [selectedEventId, setSelectedEventIdState] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshEvents = useCallback(async () => {
    if (!getToken()) return;
    const list = await getEvents();
    setEvents(list);

    const stored = localStorage.getItem(STORAGE_KEY);
    const validStored = stored && list.some((e) => e.id === stored);
    const active = list.find((e) => e.is_active);
    const nextId = validStored ? stored : active?.id ?? list[0]?.id ?? null;

    setSelectedEventIdState(nextId);
    if (nextId) localStorage.setItem(STORAGE_KEY, nextId);
  }, []);

  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    refreshEvents()
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [refreshEvents]);

  const setSelectedEventId = (id: string | null) => {
    setSelectedEventIdState(id);
    if (id) localStorage.setItem(STORAGE_KEY, id);
    else localStorage.removeItem(STORAGE_KEY);
  };

  const selectedEvent = events.find((e) => e.id === selectedEventId) ?? null;

  return (
    <EventContext.Provider
      value={{
        events,
        selectedEventId,
        selectedEvent,
        setSelectedEventId,
        loading,
        refreshEvents,
      }}
    >
      {children}
    </EventContext.Provider>
  );
}

export function useEventContext() {
  const ctx = useContext(EventContext);
  if (!ctx) throw new Error("useEventContext must be used within EventProvider");
  return ctx;
}
