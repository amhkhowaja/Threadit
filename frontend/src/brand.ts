// Brand + design tokens. Single source of truth for the whole UI.
// One calm, sober theme — intentionally no dark/light toggle.
// Edit this file to rebrand the entire app.

export const brand = {
  name: "Threadit",
  tagline: "Follow the thread.",

  color: {
    // Restrained neutral palette + one deep-green accent.
    bg: "#faf9f7",
    surface: "#ffffff",
    border: "#e6e3dd",
    text: "#1c1b19",
    textMuted: "#6b6862",
    accent: "#1f6f54", // deep green
    accentHover: "#185a44",
    accentSoft: "#e9f1ed",
    danger: "#9b2c2c",
    dangerSoft: "#fbeaea",
    focus: "#1f6f54",
  },

  font: {
    display: `"Fraunces", Georgia, "Times New Roman", serif`,
    text: `"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`,
    mono: `"IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace`,
  },

  // Modular type scale (rem).
  fontSize: {
    xs: "0.75rem",
    sm: "0.875rem",
    base: "1rem",
    lg: "1.125rem",
    xl: "1.375rem",
    "2xl": "1.75rem",
    "3xl": "2.25rem",
  },
  fontWeight: { regular: 400, medium: 500, semibold: 600 },
  lineHeight: { tight: 1.2, normal: 1.55 },

  // 4px spacing scale.
  space: {
    xs: "0.25rem",
    sm: "0.5rem",
    md: "1rem",
    lg: "1.5rem",
    xl: "2.5rem",
  },

  radius: { sm: "4px", md: "8px", lg: "12px" },
  shadow: { sm: "0 1px 2px rgba(0,0,0,0.05)", md: "0 2px 8px rgba(0,0,0,0.06)" },

  layout: { maxWidth: "720px", contentWidth: "640px" },
  breakpoint: { sm: "640px", md: "768px" },
} as const;

export type Brand = typeof brand;
