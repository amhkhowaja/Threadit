/* Injects brand tokens as CSS custom properties so components use var(--...). */
import { brand } from "./brand";

export function brandCss(): string {
  const c = brand.color;
  return `
:root {
  --bg: ${c.bg};
  --surface: ${c.surface};
  --border: ${c.border};
  --text: ${c.text};
  --text-muted: ${c.textMuted};
  --accent: ${c.accent};
  --accent-hover: ${c.accentHover};
  --accent-soft: ${c.accentSoft};
  --danger: ${c.danger};
  --danger-soft: ${c.dangerSoft};
  --focus: ${c.focus};
  --font-display: ${brand.font.display};
  --font-text: ${brand.font.text};
  --font-mono: ${brand.font.mono};
  --radius-sm: ${brand.radius.sm};
  --radius-md: ${brand.radius.md};
  --radius-lg: ${brand.radius.lg};
  --max-width: ${brand.layout.maxWidth};
  --content-width: ${brand.layout.contentWidth};
}
* { box-sizing: border-box; }
html, body, #root { height: 100%; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-text);
  font-size: ${brand.fontSize.base};
  line-height: ${brand.lineHeight.normal};
  -webkit-font-smoothing: antialiased;
}
h1, h2, h3 { font-family: var(--font-display); font-weight: ${brand.fontWeight.semibold}; line-height: ${brand.lineHeight.tight}; margin: 0 0 ${brand.space.sm}; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
button { font-family: inherit; }
:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
code, pre { font-family: var(--font-mono); }
`;
}
