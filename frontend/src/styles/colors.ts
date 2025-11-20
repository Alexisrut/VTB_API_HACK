// This file colors for recharts

export const primary_hsl = "270 80% 65%";
export const accent_hsl = "180 95% 55%";

export const primary = `hsl(${primary_hsl})`;
export const accent = `hsl(${accent_hsl})`;

export const danger = `hsl(0 72% 58%)`;
export const border = `hsl(240 8% 18%)`;
export const muted_foreground = `hsl(210 20% 65%)`;
export const popover = `hsl(240 8% 12%)`;

export const primaryHslParts = primary_hsl.split(" ");
export const accentHslParts = accent_hsl.split(" ");

export default {
  primary,
  accent,
  danger,
  border,
  muted_foreground,
  popover,
};
