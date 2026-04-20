/**
 * Back — navigation back button.
 *
 * Props:
 *   label   string?  — button label (default: "Volver")
 *   onClick fn
 */
export function Back({ label, onClick }) {
  return (
    <button onClick={onClick} className="back-btn" aria-label={`Volver a ${label || "la vista anterior"}`}>
      ‹ {label || "Volver"}
    </button>
  );
}
