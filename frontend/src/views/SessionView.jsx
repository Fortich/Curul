import { Tag } from "../components/Tag";
import { IdeaCard } from "../components/IdeaCard";
import { Back } from "../components/Back";
import { fmtDate } from "../utils";

/**
 * SessionView — list of ideas for a single plenary session.
 *
 * Props:
 *   sessionId   string
 *   sessions    Session[]
 *   getIdeas    fn(opts) → Idea[]
 *   goSenator   fn(name)
 *   goTheme     fn(tag, sessionId?)
 *   goBack      fn
 */
export function SessionView({ sessionId, sessions, getIdeas, goSenator, goTheme, goBack }) {
  const session = sessions.find((x) => x.session === sessionId);
  const date = session?.date ?? "";
  const ideas = getIdeas({ session: sessionId }).sort((a, b) => a.start - b.start);

  const tagFreq = {};
  ideas.forEach((i) => i.tags.forEach((t) => { tagFreq[t] = (tagFreq[t] || 0) + 1; }));

  return (
    <>
      <Back label="Sesiones" onClick={goBack} />

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
              onClick={() => goTheme(t, sessionId)}
            />
          ))}
      </div>

      <p className="view-count">{ideas.length} intervenciones · orden cronológico</p>

      {ideas.map((idea, i) => (
        <IdeaCard
          key={`${idea.congressman_name}-${idea.start}`}
          idea={idea}
          onSenatorClick={goSenator}
          delay={0.04 * i}
          youtubeUrl={session?.youtube_url}
        />
      ))}
    </>
  );
}
