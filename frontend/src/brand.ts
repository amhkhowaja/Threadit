// Brand + design tokens. Single source of truth for the whole UI.
// One calm, sober theme — intentionally no dark/light toggle.
// Edit this file to rebrand the entire app.

export const brand = {
  name: "Threadit",
  tagline: "Follow the thread.",

  color: {
    // Restrained neutral palette + one deep-green accent.
    bg: "#f6f5f2",
    surface: "#ffffff",
    surface2: "#faf9f7",
    border: "#e7e4de",
    text: "#17100f",
    textMuted: "#6b675f",
    accent: "#1f6f54", // deep green
    accentHover: "#185a44",
    accentSoft: "#e9f1ed",
    danger: "#b4342f",
    dangerSoft: "#fbeceb",
    focus: "#1f6f54",
  },

  font: {
    display: `"Fraunces", Georgia, "Times New Roman", serif`,
    text: `"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`,
    mono: `"IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace`,
  },

  // Modular type scale (rem) — larger, more confident.
  fontSize: {
    xs: "0.78rem",
    sm: "0.9rem",
    base: "1rem",
    lg: "1.2rem",
    xl: "1.5rem",
    "2xl": "2rem",
    "3xl": "2.6rem",
  },
  fontWeight: { regular: 400, medium: 500, semibold: 600 },
  lineHeight: { tight: 1.15, normal: 1.65 },

  // 4px spacing scale.
  space: {
    xs: "0.25rem",
    sm: "0.5rem",
    md: "1rem",
    lg: "1.5rem",
    xl: "2.5rem",
  },

  radius: { sm: "6px", md: "10px", lg: "16px" },
  shadow: { sm: "0 1px 2px rgba(0,0,0,0.05)", md: "0 2px 8px rgba(0,0,0,0.06)" },

  layout: { maxWidth: "1100px", contentWidth: "820px", readMeasure: "68ch" },
  breakpoint: { sm: "640px", md: "768px" },
} as const;

export type Brand = typeof brand;
