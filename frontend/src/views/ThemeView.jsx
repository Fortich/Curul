import { IdeaCard } from "../components/IdeaCard";
import { Tag } from "../components/Tag";
import { Back } from "../components/Back";
import { shortName } from "../utils";

/**
 * ThemeView — all ideas tagged with a given topic.
 *
 * Props:
 *   tag        string
 *   sessionId  string?   — if set, scoped to one session
 *   sessions   Session[]
 *   getIdeas   fn(opts) → Idea[]
 *   goSenator  fn(name)
 *   goBack     fn
 */
export function ThemeView({ tag, sessionId, sessions, getIdeas, goSenator, goBack }) {
  const ideas = getIdeas({ tag, session: sessionId }).sort(
    (a, b) => b.importance - a.importance
  );
  const contributors = {};
  ideas.forEach((i) => {
    contributors[i.congressman_name] = (contributors[i.congressman_name] || 0) + 1;
  });

  return (
    <>
      <Back label="Volver" onClick={goBack} />

      <div className="theme-header">
        <Tag tag={tag} size="md" />

        <p>
          {ideas.length} intervención{ideas.length !== 1 ? "es" : ""}
          {sessionId ? "" : " en todas las sesiones"}
        </p>

        {Object.keys(contributors).length > 1 && (
          <div className="theme-contributors">
            {Object.entries(contributors)
              .sort((a, b) => b[1] - a[1])
              .map(([name]) => (
                <button
                  key={name}
                  className="theme-contributor-btn"
                  onClick={() => goSenator(name)}
                >
                  {shortName(name)}
                </button>
              ))}
          </div>
        )}
      </div>

      {ideas.map((idea, i) => (
        <IdeaCard
          key={`${idea.congressman_name}-${idea.start}`}
          idea={idea}
          onSenatorClick={goSenator}
          delay={0.04 * i}
          youtubeUrl={sessions.find((x) => x.session === idea.session)?.youtube_url}
        />
      ))}
    </>
  );
}
