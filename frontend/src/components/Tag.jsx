import { tagColors } from "../utils";

/**
 * Tag — colored pill label derived from the tag string.
 *
 * Props:
 *   tag      string   — label text
 *   size     "sm"|"md"
 *   onClick  fn?      — makes the tag clickable
 *   active   bool?    — shows a border when true, fades when false
 */
export function Tag({ tag, onClick, active, size = "sm" }) {
  const { bg, text } = tagColors(tag);
  const sizeClass = size === "md" ? "md" : "sm";
  const activeClass = active === true ? "active" : active === false ? "inactive" : "";
  const clickClass = onClick ? "clickable" : "";

  return (
    <span
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={onClick ? (e) => (e.key === "Enter" || e.key === " ") && onClick(e) : undefined}
      className={["tag", sizeClass, activeClass, clickClass].filter(Boolean).join(" ")}
      style={{ background: bg, color: text }}
    >
      {tag}
    </span>
  );
}
