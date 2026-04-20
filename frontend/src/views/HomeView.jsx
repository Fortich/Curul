import { SessionCard } from "../components/SessionCard";
import { SenatorRow } from "../components/SenatorRow";
import { Tag } from "../components/Tag";

/**
 * HomeView — landing page with sessions, senators, and themes.
 *
 * Props:
 *   sessions     Session[]
 *   allSenators  { name, count, sessions }[]
 *   globalTags   [string, number][]
 *   getIdeas     fn(opts) → Idea[]
 *   push         fn(navEntry)
 */
export function HomeView({ sessions, allSenators, globalTags, getIdeas, push }) {
  return (
    <>
      {/* Sessions */}
      <section className="section-block" aria-labelledby="heading-sessions">
        <h2 id="heading-sessions" className="section-heading">
          <span className="marker" aria-hidden="true">■</span>
          Sesiones plenarias
        </h2>

        {sessions.map((s, i) => {
          const ideas = getIdeas({ session: s.session });
          return (
            <SessionCard
              key={s.session}
              session={s}
              count={ideas.length}
              senators={new Set(ideas.map((x) => x.congressman_name)).size}
              onClick={() => push({ view: "session", session: s.session })}
              delay={0.06 * i}
              isLatest={i === 0}
            />
          );
        })}

        <p className="more-sessions-note">
          Más sesiones pronto — procesando el archivo histórico
        </p>
      </section>

      {/* Senators */}
      <section className="section-block" aria-labelledby="heading-senators">
        <h2 id="heading-senators" className="section-heading">
          <span className="marker" aria-hidden="true">■</span>
          Senadores
        </h2>

        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {allSenators.map((s, i) => (
            <SenatorRow
              key={s.name}
              name={s.name}
              count={s.count}
              sessions={s.sessions}
              onClick={() => push({ view: "senator", senator: s.name })}
              delay={0.04 * i}
            />
          ))}
        </div>
      </section>

      {/* Themes */}
      <section aria-labelledby="heading-themes">
        <h2 id="heading-themes" className="section-heading">
          <span className="marker" aria-hidden="true">■</span>
          Temas
        </h2>

        <div className="tags-row">
          {globalTags.map(([t], i) => (
            <span
              key={t}
              style={{ cursor: "pointer", animation: `fadeIn .35s ease ${0.03 * i}s both` }}
            >
              <Tag
                tag={t}
                size="md"
                onClick={() => push({ view: "theme", tag: t })}
              />
            </span>
          ))}
        </div>
      </section>
    </>
  );
}
