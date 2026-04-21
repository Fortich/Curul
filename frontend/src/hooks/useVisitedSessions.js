import { useCallback, useEffect, useRef } from "react";

const STORAGE_KEY = "curul:visited-sessions";

/**
 * useVisitedSessions — persists which sessions the user has seen.
 *
 * Returns:
 *   hasVisited(sessionId)  → bool
 *   markVisited(sessionId) → void   (call when opening a session)
 */
export function useVisitedSessions() {
  const setRef = useRef(new Set(JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]")));

  const persist = useCallback(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...setRef.current]));
  }, []);

  const hasVisited = useCallback((id) => setRef.current.has(id), []);

  const markVisited = useCallback((id) => {
    if (!setRef.current.has(id)) {
      setRef.current.add(id);
      persist();
    }
  }, [persist]);

  return { hasVisited, markVisited };
}
