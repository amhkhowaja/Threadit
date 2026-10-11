import type { Config } from "tailwindcss";

// Theme reads CSS variables injected from brand.ts (see src/theme.ts),
// so brand.ts remains the single source of truth for rebranding.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        "surface-2": "var(--surface-2)",
        border: "var(--border)",
        text: "var(--text)",
        muted: "var(--text-muted)",
        accent: "var(--accent)",
        "accent-hover": "var(--accent-hover)",
        "accent-soft": "var(--accent-soft)",
        danger: "var(--danger)",
        "danger-soft": "var(--danger-soft)",
      },
      fontFamily: {
        display: "var(--font-display)",
        sans: "var(--font-text)",
        mono: "var(--font-mono)",
      },
      borderRadius: {
        DEFAULT: "var(--radius-md)",
        sm: "var(--radius-sm)",
        lg: "var(--radius-lg)",
      },
      maxWidth: {
        content: "var(--content-width)",
        shell: "var(--max-width)",
      },
      boxShadow: {
        card: "0 1px 2px rgba(17,16,15,0.04), 0 1px 3px rgba(17,16,15,0.06)",
        lift: "0 4px 14px rgba(17,16,15,0.08)",
      },
    },
  },
  plugins: [],
} satisfies Config;
