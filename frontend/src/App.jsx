import { useState, useMemo } from "react";
import { useData } from "./useData";
import { HomeView } from "./views/HomeView";
import { SessionView } from "./views/SessionView";
import { SenatorView } from "./views/SenatorView";
import { ThemeView } from "./views/ThemeView";

/**
 * App — shell: data, navigation stack, layout chrome.
 * No business logic, no inline styles, no view rendering.
 * ~70 lines.
 */
export default function App() {
  const { sessions, ideas: ideasData, loading } = useData();
  const [nav, setNav] = useState([{ view: "home" }]);
  const current = nav[nav.length - 1];

  // ── Navigation ────────────────────────────────────────────
  const push = (entry) => { setNav((prev) => [...prev, entry]); window.scrollTo({ top: 0 }); };
  const pop  = ()      => { setNav((prev) => prev.length > 1 ? prev.slice(0, -1) : [{ view: "home" }]); window.scrollTo({ top: 0 }); };

  // ── Derived data ──────────────────────────────────────────
  const allSenators = useMemo(() => {
    const map = {};
    ideasData.forEach((i) => {
      if (!map[i.congressman_name]) map[i.congressman_name] = { count: 0, sessions: new Set() };
      map[i.congressman_name].count++;
      map[i.congressman_name].sessions.add(i.session);
    });
    return Object.entries(map)
      .map(([name, d]) => ({ name, count: d.count, sessions: d.sessions.size }))
      .sort((a, b) => b.count - a.count);
  }, [ideasData]);

  const globalTags = useMemo(() => {
    const map = {};
    ideasData.forEach((i) => i.tags.forEach((t) => { map[t] = (map[t] || 0) + 1; }));
    return Object.entries(map).sort((a, b) => b[1] - a[1]);
  }, [ideasData]);

  const getIdeas = ({ session, senator, tag } = {}) => {
    let ideas = ideasData;
    if (session) ideas = ideas.filter((i) => i.session === session);
    if (senator) ideas = ideas.filter((i) => i.congressman_name === senator);
    if (tag)     ideas = ideas.filter((i) => i.tags.includes(tag));
    return ideas;
  };

  // ── Loading ───────────────────────────────────────────────
  if (loading) return <div className="loading">Cargando…</div>;

  // ── Shared view props ─────────────────────────────────────
  const viewProps = { sessions, getIdeas, push, pop };

  // ── Render ────────────────────────────────────────────────
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-inner">
          <button className="app-logo" onClick={() => setNav([{ view: "home" }])}>
            Curul
          </button>
          <span className="app-badge">Senado de Colombia</span>
        </div>
        <p className="app-tagline">Lo que dicen tus senadores, en sus propias palabras.</p>
      </header>

      <main className="app-main">
        {current.view === "home" && (
          <HomeView allSenators={allSenators} globalTags={globalTags} {...viewProps} />
        )}
        {current.view === "session" && (
          <SessionView sessionId={current.session} {...viewProps} />
        )}
        {current.view === "senator" && (
          <SenatorView senatorName={current.senator} {...viewProps} />
        )}
        {current.view === "theme" && (
          <ThemeView tag={current.tag} sessionId={current.session} {...viewProps} />
        )}

        <footer className="app-footer">
          <p>
            Curul — Transparencia legislativa para Colombia<br />
            Datos extraídos de sesiones plenarias del Senado
          </p>
        </footer>
      </main>
    </div>
  );
}
