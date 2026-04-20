import { avatarCol, initials, displayName } from "../utils";

/**
 * SenatorRow — a single row in the senators list.
 *
 * Props:
 *   name      string   — full congressman name
 *   count     number   — total interventions
 *   sessions  number   — sessions appeared in
 *   onClick   fn
 *   delay     number   — animation delay in seconds
 */
export function SenatorRow({ name, count, sessions, onClick, delay = 0 }) {
  return (
    <button
      onClick={onClick}
      className="card senator-row"
      style={{ animationDelay: `${delay}s` }}
      aria-label={`Ver perfil de ${displayName(name)}, ${count} intervenciones`}
    >
      <div
        className="avatar"
        style={{ width: 42, height: 42, fontSize: 14, background: avatarCol(name) }}
        aria-hidden="true"
      >
        {initials(name)}
      </div>

      <div style={{ flex: 1 }}>
        <div className="senator-row-name">{displayName(name)}</div>
        {sessions > 1 && (
          <div className="senator-row-sessions">en {sessions} sesiones</div>
        )}
      </div>

      <span className="senator-row-count" aria-label={`${count} intervenciones`}>
        {count}
      </span>
      <span className="senator-row-arrow" aria-hidden="true">›</span>
    </button>
  );
}
