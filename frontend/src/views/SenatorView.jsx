import { avatarCol, initials, displayName, fmtDate } from "../utils";
import { IdeaCard } from "../components/IdeaCard";
import { Back } from "../components/Back";
import POSITIONS from "../positions.json";

/**
 * SenatorView — senator profile with consolidated positions.
 *
 * Props:
 *   senatorName  string
 *   sessions     Session[]
 *   getIdeas     fn(opts) → Idea[]
 *   goSession    fn(id)
 *   goBack       fn
 */
export function SenatorView({ senatorName, sessions, getIdeas, goSession, goBack }) {
  const ideas   = getIdeas({ senator: senatorName }).sort((a, b) => a.start - b.start);
  const sessionIds = [...new Set(ideas.map((i) => i.session))];
  const avatarColor = avatarCol(senatorName);
  const position = POSITIONS[senatorName];

  return (
    <>
      <Back label="Volver" onClick={goBack} />

      {/* ── Header ───────────────────────────────────────── */}
      <header className="senator-profile-header">
        <div
          className="avatar"
          style={{ width: 52, height: 52, fontSize: 18, background: avatarColor }}
          aria-hidden="true"
        >
          {initials(senatorName)}
        </div>
        <div className="senator-profile-meta">
          <h2>{displayName(senatorName)}</h2>
          <p>
            {ideas.length} intervención{ideas.length !== 1 ? "es" : ""}
            {sessionIds.length > 1 ? ` en ${sessionIds.length} sesiones` : ""}
          </p>
        </div>
      </header>

      {/* ── Consolidated summary ─────────────────────────── */}
      {position?.consolidated_summary && (
        <div className="senator-summary">
          <p>{position.consolidated_summary}</p>
        </div>
      )}

      {/* ── Main themes ──────────────────────────────────── */}
      {position?.main_themes?.length > 0 && (
        <div className="senator-themes">
          <p className="senator-section-label">Temas principales</p>
          <div className="tags-row">
            {position.main_themes.map((t) => {
              // Derive color the same way tagColors does in utils.js
              let h = 0;
              for (let i = 0; i < t.length; i++) h = t.charCodeAt(i) + ((h << 5) - h);
              const hue = Math.abs(h) % 360;
              const bg   = `hsl(${hue},18%,19%)`;
              const text = `hsl(${hue},45%,72%)`;
              return (
                <span
                  key={t}
                  style={{
                    display: "inline-flex", alignItems: "center",
                    borderRadius: "100px", fontFamily: "var(--font-ui)",
                    fontWeight: 500, whiteSpace: "nowrap",
                    background: bg, color: text,
                    padding: "5px 14px", fontSize: 12,
                  }}
                >
                  {t}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Key positions ────────────────────────────────── */}
      {position?.key_positions?.length > 0 && (
        <div className="senator-positions">
          <p className="senator-section-label">Posiciones clave</p>
          <ul className="senator-positions-list">
            {position.key_positions.map((pos, i) => (
              <li key={i}>{pos}</li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Speeches ─────────────────────────────────────── */}
      <div className="senator-ideas-header">
        <p className="senator-section-label">
          Intervenciones{sessionIds.length > 1 ? ` (${sessionIds.length} sesiones)` : ""}
        </p>
      </div>

      {sessionIds.length > 1
        ? sessionIds.map((sid) => {
            const sessionIdeas = ideas.filter((i) => i.session === sid);
            const sessionData  = sessions.find((x) => x.session === sid);
            const date         = sessionData?.date ?? "";
            return (
              <div key={sid} style={{ marginBottom: "24px" }}>
                <button className="session-group-label" onClick={() => goSession(sid)}>
                  {date ? fmtDate(date) : sid}
                </button>
                {sessionIdeas.map((idea, i) => (
                  <IdeaCard
                    key={`${idea.congressman_name}-${idea.start}`}
                    idea={idea}
                    delay={0.04 * i}
                    youtubeUrl={sessionData?.youtube_url}
                  />
                ))}
              </div>
            );
          })
        : ideas.map((idea, i) => (
            <IdeaCard
              key={`${idea.congressman_name}-${idea.start}`}
              idea={idea}
              delay={0.05 * i}
              youtubeUrl={sessions.find((x) => x.session === idea.session)?.youtube_url}
            />
          ))}
    </>
  );
}
