import { avatarCol, initials, displayName, fmtDate } from "../utils";
import { IdeaCard } from "../components/IdeaCard";
import { Back } from "../components/Back";

/**
 * SenatorView — profile page for a single senator.
 *
 * Props:
 *   senatorName  string
 *   sessions     Session[]
 *   getIdeas     fn(opts) → Idea[]
 *   push         fn(navEntry)
 *   pop          fn
 */
export function SenatorView({ senatorName, sessions, getIdeas, push, pop }) {
  const ideas = getIdeas({ senator: senatorName }).sort((a, b) => a.start - b.start);
  const sessionIds = [...new Set(ideas.map((i) => i.session))];
  const avatarColor = avatarCol(senatorName);

  return (
    <>
      <Back label="Volver" onClick={pop} />

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

      {sessionIds.length > 1
        ? sessionIds.map((sid) => {
            const sessionIdeas = ideas.filter((i) => i.session === sid);
            const sessionData = sessions.find((x) => x.session === sid);
            const date = sessionData?.date ?? "";

            return (
              <div key={sid} style={{ marginBottom: "24px" }}>
                <button
                  className="session-group-label"
                  onClick={() => push({ view: "session", session: sid })}
                >
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
