import { Tag } from "../components/Tag";
import { IdeaCard } from "../components/IdeaCard";
import { Back } from "../components/Back";
import { fmtDate } from "../utils";

/**
 * SessionView — list of ideas for a single plenary session.
 *
 * Props:
 *   sessionId  string
 *   sessions   Session[]
 *   getIdeas   fn(opts) → Idea[]
 *   push       fn(navEntry)
 *   pop        fn
 */
export function SessionView({ sessionId, sessions, getIdeas, push, pop }) {
  const session = sessions.find((x) => x.session === sessionId);
  const date = session?.date ?? "";
  const ideas = getIdeas({ session: sessionId }).sort((a, b) => a.start - b.start);

  // Build tag frequency from ideas
  const tagFreq = {};
  ideas.forEach((i) => i.tags.forEach((t) => { tagFreq[t] = (tagFreq[t] || 0) + 1; }));

  return (
    <>
      <Back label="Sesiones" onClick={pop} />

      <h2 className="view-title">Sesión Plenaria</h2>
      {date && <p className="view-accent-date">{fmtDate(date)}</p>}
      <p className="view-summary">{session?.summary}</p>

      <div className="tags-row" style={{ marginBottom: "20px" }}>
        {Object.entries(tagFreq)
          .sort((a, b) => b[1] - a[1])
          .map(([t]) => (
            <Tag
              key={t}
              tag={t}
              size="sm"
              onClick={() => push({ view: "theme", tag: t, session: sessionId })}
            />
          ))}
      </div>

      <p className="view-count">{ideas.length} intervenciones · orden cronológico</p>

      {ideas.map((idea, i) => (
        <IdeaCard
          key={`${idea.congressman_name}-${idea.start}`}
          idea={idea}
          onSenatorClick={(name) => push({ view: "senator", senator: name })}
          delay={0.04 * i}
          youtubeUrl={session?.youtube_url}
        />
      ))}
    </>
  );
}
