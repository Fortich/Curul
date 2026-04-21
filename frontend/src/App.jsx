import { useMemo } from "react";
import { BrowserRouter, Routes, Route, useNavigate, useParams, Navigate } from "react-router-dom";
import { useData } from "./useData";
import { HomeView } from "./views/HomeView";
import { SessionView } from "./views/SessionView";
import { SenatorView } from "./views/SenatorView";
import { ThemeView } from "./views/ThemeView";

/**
 *   /                     → HomeView
 *   /sesion/:id           → SessionView
 *   /senador/:nombre      → SenatorView  (nombre URL-encoded)
 *   /tema/:tag            → ThemeView    (tag URL-encoded)
 */
export default function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  );
}

function AppShell() {
  const { sessions, ideas: ideasData, loading } = useData();
  const navigate = useNavigate();

  // ── Navigation ────────────────────────────────────────────
  const goHome    = ()       => navigate("/");
  const goSession = (id)     => navigate(`/sesion/${encodeURIComponent(id)}`);
  const goSenator = (name)   => navigate(`/senador/${encodeURIComponent(name)}`);
  const goTheme   = (tag, session) =>
    navigate(`/tema/${encodeURIComponent(tag)}${session ? `?sesion=${encodeURIComponent(session)}` : ""}`);
  const goBack    = ()       => navigate(-1);

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

  // ── Shared props ──────────────────────────────────────────
  const nav = { goHome, goSession, goSenator, goTheme, goBack };
  const data = { sessions, getIdeas };

  // ── Render ────────────────────────────────────────────────
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-inner">
          <button className="app-logo" onClick={goHome}>Curul</button>
          <span className="app-badge">Senado de Colombia</span>
        </div>
        <p className="app-tagline">Lo que dicen tus senadores, en sus propias palabras.</p>
      </header>

      <main className="app-main">
        <Routes>
          <Route
            path="/"
            element={<HomeView allSenators={allSenators} globalTags={globalTags} {...data} {...nav} />}
          />
          <Route
            path="/sesion/:id"
            element={<SessionRoute {...data} {...nav} />}
          />
          <Route
            path="/senador/:nombre"
            element={<SenatorRoute {...data} {...nav} />}
          />
          <Route
            path="/tema/:tag"
            element={<ThemeRoute {...data} {...nav} />}
          />
          {/* Fallback — redirects unknown routes to home */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>

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

// ── Route wrappers — extract params from the URL ──────────────

function SessionRoute(props) {
  const { id } = useParams();
  return <SessionView sessionId={decodeURIComponent(id)} {...props} />;
}

function SenatorRoute(props) {
  const { nombre } = useParams();
  return <SenatorView senatorName={decodeURIComponent(nombre)} {...props} />;
}

function ThemeRoute(props) {
  const { tag } = useParams();
  const sessionId = new URLSearchParams(window.location.search).get("sesion");
  return (
    <ThemeView
      tag={decodeURIComponent(tag)}
      sessionId={sessionId ? decodeURIComponent(sessionId) : undefined}
      {...props}
    />
  );
}
