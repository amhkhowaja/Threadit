// Emits brand tokens as CSS custom properties consumed by Tailwind + base CSS.
import { brand } from "./brand";

export function brandCssVars(): string {
  const c = brand.color;
  return `:root{
  --bg:${c.bg};
  --surface:${c.surface};
  --surface-2:${c.surface2};
  --border:${c.border};
  --text:${c.text};
  --text-muted:${c.textMuted};
  --accent:${c.accent};
  --accent-hover:${c.accentHover};
  --accent-soft:${c.accentSoft};
  --danger:${c.danger};
  --danger-soft:${c.dangerSoft};
  --focus:${c.focus};
  --font-display:${brand.font.display};
  --font-text:${brand.font.text};
  --font-mono:${brand.font.mono};
  --radius-sm:${brand.radius.sm};
  --radius-md:${brand.radius.md};
  --radius-lg:${brand.radius.lg};
  --max-width:${brand.layout.maxWidth};
  --content-width:${brand.layout.contentWidth};
  --read-measure:${brand.layout.readMeasure};
}`;
}
