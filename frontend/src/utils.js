const AVATAR_COLORS = [
  "#4f86c6", "#e07b54", "#5bb86a", "#c45c8a",
  "#7c60c2", "#c8a33b", "#3aacb8", "#d95f5f",
];

const _MONTHS_ES = {
  enero:1, febrero:2, marzo:3, abril:4, mayo:5, junio:6,
  julio:7, agosto:8, septiembre:9, octubre:10, noviembre:11, diciembre:12,
};

/** Derives display metadata from a pipeline session name like "Abril-08-26".
 *  Returns { title, date } where date is "YYYY-MM-DD". */
export const parseSessionName = name => {
  const parts = name.toLowerCase().split("-");
  const month = _MONTHS_ES[parts[0]];
  if (!month || parts.length < 3) return { title: "Sesión Plenaria", date: "" };
  const year = 2000 + parseInt(parts[parts.length - 1], 10);
  const day  = parseInt(parts[1], 10);
  return {
    title: "Sesión Plenaria",
    date:  `${year}-${String(month).padStart(2,"0")}-${String(day).padStart(2,"0")}`,
  };
};

export const fmt = s => `${Math.floor(s/60)}:${String(Math.floor(s%60)).padStart(2,'0')}`;

export const initials = n => {
  const p = n.split(' ');
  return p.length >= 3
    ? (p[p.length-2][0] + p[p.length-1][0]).toUpperCase()
    : (p[0][0] + (p[1]?.[0] || '')).toUpperCase();
};

export const displayName = n => {
  const p = n.split(' ');
  return p.length >= 3 ? p.slice(-2).join(' ') + ', ' + p.slice(0,-2).join(' ') : n;
};

export const shortName = n => {
  const p = n.split(' ');
  return p.length >= 3 ? `${p[p.length-1]} ${p[0]}` : n;
};

export const avatarCol = n => {
  let h = 0;
  for (let i = 0; i < n.length; i++) h = n.charCodeAt(i) + ((h << 5) - h);
  return AVATAR_COLORS[Math.abs(h) % AVATAR_COLORS.length];
};

export const tagColors = tag => {
  let h = 0;
  for (let i = 0; i < tag.length; i++) h = tag.charCodeAt(i) + ((h << 5) - h);
  const hue = Math.abs(h) % 360;
  return { bg: `hsl(${hue},35%,18%)`, text: `hsl(${hue},70%,78%)` };
};

export const fmtDate = d =>
  new Date(d + "T12:00:00").toLocaleDateString("es-CO", { day:"numeric", month:"long", year:"numeric" });

export const ago = d => {
  const days = Math.floor((new Date("2026-04-14") - new Date(d)) / 864e5);
  return days < 1 ? "Hoy"
    : days === 1 ? "Ayer"
    : days < 7 ? `Hace ${days} días`
    : days < 30 ? `Hace ${Math.floor(days/7)} sem.`
    : days < 365 ? `Hace ${Math.floor(days/30)} meses`
    : "Hace más de 1 año";
};
