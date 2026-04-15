/**
 * Data layer — single place to swap the data source.
 *
 * Today: returns the static JS bundle (data.js).
 * Future: replace the body of useData() to fetch from an API endpoint,
 * a JSON file, or any other source — the rest of the app stays the same.
 *
 * Returned shape:
 *   {
 *     sessions: Session[],
 *     ideas:    Idea[],
 *     loading:  boolean,
 *     error:    Error | null,
 *   }
 */

import { useState, useEffect } from "react";
import { SESSIONS, IDEAS_DATA } from "./data";

export function useData() {
  const [state, setState] = useState({ sessions: [], ideas: [], loading: true, error: null });

  useEffect(() => {
    // ── Static source ────────────────────────────────────────────────────────
    // Replace this block with a fetch() call when a real endpoint is ready.
    // Example:
    //   const [sessions, ideas] = await Promise.all([
    //     fetch("/api/sessions").then(r => r.json()),
    //     fetch("/api/ideas").then(r => r.json()),
    //   ]);
    setState({ sessions: SESSIONS, ideas: IDEAS_DATA, loading: false, error: null });
    // ─────────────────────────────────────────────────────────────────────────
  }, []);

  return state;
}
