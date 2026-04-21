import { avatarCol, initials, displayName, fmt, fmtDate, ago } from "../utils";
import { Tag } from "./Tag";

/**
 * SessionCard — summary card for a plenary session.
 *
 * Props:
 *   session    Session object
 *   count      number   — total ideas in this session
 *   senators   number   — unique senators in this session
 *   onClick    fn
 *   delay      number   — animation delay in seconds
 *   isLatest   bool     — first session in the list
 *   isNew      bool     — the user has not visited this session yet
 */
export function SessionCard({ session, count, senators, onClick, delay = 0, isLatest = false, isNew = false }) {
  const date = session.date ?? "";
  const isRecent = isLatest || (date && (new Date() - new Date(date + "T12:00:00")) < 7 * 864e5);
  const showNewBadge = isNew && isRecent;

  return (
    <button
      onClick={onClick}
      className="card session-card"
      style={{ animationDelay: `${delay}s`, width: "100%", textAlign: "left", display: "block" }}
      aria-label={`Ver sesión plenaria del ${date ? fmtDate(date) : session.session}`}
    >
      <div className={`session-card-stripe ${isRecent ? "is-recent" : ""}`} />

      <div className="session-card-meta">
        <div className="session-card-meta-left">
          {showNewBadge && <span className="badge-new">Nueva</span>}
          {date && <span className="session-card-date">{ago(date)}</span>}
        </div>
        <span className="session-card-arrow">›</span>
      </div>

      <h3 className="session-card-title">Sesión Plenaria</h3>
      {date && <p className="session-card-accent-date">{fmtDate(date)}</p>}

      <p className="session-card-summary">{session.summary}</p>

      {/* Show top themes from session data — field was unused before */}
      {session.themes?.length > 0 && (
        <div className="tags-row" style={{ marginBottom: "14px" }}>
          {session.themes.slice(0, 5).map((t) => (
            <Tag key={t} tag={t} size="sm" />
          ))}
          {session.themes.length > 5 && (
            <span style={{ fontSize: "11px", color: "var(--text-tertiary)", alignSelf: "center" }}>
              +{session.themes.length - 5}
            </span>
          )}
        </div>
      )}

      <div className="session-card-stats">
        <span>{senators} senadores</span>
        <span>·</span>
        <span>{count} intervenciones</span>
      </div>
    </button>
  );
}
