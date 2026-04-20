import { useState } from "react";
import { avatarCol, initials, displayName, fmt } from "../utils";
import { Tag } from "./Tag";

/**
 * IdeaCard — a single congressional intervention.
 *
 * Props:
 *   idea           Idea object
 *   onSenatorClick fn?       — called with congressman_name
 *   delay          number    — animation delay in seconds
 *   youtubeUrl     string?
 */
export function IdeaCard({ idea, onSenatorClick, delay = 0, youtubeUrl }) {
  const [open, setOpen] = useState(false);
  const avatarColor = avatarCol(idea.congressman_name);

  const importanceClass =
    idea.importance >= 0.7 ? "high" : idea.importance >= 0.5 ? "medium" : "low";

  const importanceLabel =
    idea.importance >= 0.7 ? "Alta relevancia"
    : idea.importance >= 0.5 ? "Relevancia media"
    : "Baja relevancia";

  return (
    <article
      className="card idea-card"
      style={{ animationDelay: `${delay}s` }}
      aria-label={`Intervención de ${displayName(idea.congressman_name)}`}
    >
      <div className="idea-card-header">
        {/* Avatar */}
        <div
          className={`avatar ${onSenatorClick ? "clickable" : ""}`}
          style={{ width: 40, height: 40, fontSize: 13, background: avatarColor }}
          onClick={() => onSenatorClick?.(idea.congressman_name)}
          role={onSenatorClick ? "button" : undefined}
          tabIndex={onSenatorClick ? 0 : undefined}
          aria-label={onSenatorClick ? `Ver perfil de ${displayName(idea.congressman_name)}` : undefined}
          onKeyDown={onSenatorClick
            ? (e) => (e.key === "Enter" || e.key === " ") && onSenatorClick(idea.congressman_name)
            : undefined}
        >
          {initials(idea.congressman_name)}
        </div>

        {/* Name + time */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            className={`avatar-name ${onSenatorClick ? "clickable" : ""}`}
            onClick={() => onSenatorClick?.(idea.congressman_name)}
            role={onSenatorClick ? "button" : undefined}
            tabIndex={onSenatorClick ? 0 : undefined}
            onKeyDown={onSenatorClick
              ? (e) => (e.key === "Enter" || e.key === " ") && onSenatorClick(idea.congressman_name)
              : undefined}
          >
            {displayName(idea.congressman_name)}
          </div>
          <div className="avatar-time">
            {fmt(idea.start)} – {fmt(idea.end)}
          </div>
        </div>

        {/* Importance indicator */}
        <div
          className={`importance-dot ${importanceClass}`}
          title={importanceLabel}
          aria-label={importanceLabel}
          role="img"
        />
      </div>

      {/* Summary */}
      <p className="idea-card-body">{idea.summary}</p>

      {/* Tags */}
      <div className="tags-row">
        {idea.tags.map((t) => <Tag key={t} tag={t} />)}
      </div>

      {/* Quote toggle */}
      <button
        className="idea-card-toggle"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-controls={`quote-${idea.congressman_name}-${idea.start}`}
      >
        {open ? "Ocultar cita" : "Ver cita textual"}
        <span className={`chevron ${open ? "open" : ""}`}>▾</span>
      </button>

      {/* Quote panel */}
      {open && (
        <div
          id={`quote-${idea.congressman_name}-${idea.start}`}
          className="idea-card-quote"
        >
          <p>«{idea.quote}»</p>

          {youtubeUrl && (
            <a
              href={`${youtubeUrl}&t=${Math.floor(idea.start)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="idea-card-quote-link"
            >
              ▶ Ver en YouTube · {fmt(idea.start)}
            </a>
          )}

          {idea.mentions.length > 0 && (
            <div className="idea-card-mentions">
              {idea.mentions.map((m, i) => (
                <span key={i} className="idea-card-mention">{m.entity}</span>
              ))}
            </div>
          )}
        </div>
      )}
    </article>
  );
}
