import { brand } from "../brand";

// Threadit mark: a root node branching into threaded replies (a discussion thread).
export function Logo({ size = 24 }: { size?: number }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: brand.space.sm }}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M6 4v9a3 3 0 0 0 3 3h6"
          stroke={brand.color.accent}
          strokeWidth="2"
          strokeLinecap="round"
        />
        <circle cx="6" cy="4" r="2.4" fill={brand.color.accent} />
        <circle cx="15" cy="16" r="2.4" fill={brand.color.accent} />
        <circle cx="18" cy="9" r="2" fill={brand.color.accent} opacity="0.55" />
        <path
          d="M6 9h7"
          stroke={brand.color.accent}
          strokeWidth="2"
          strokeLinecap="round"
          opacity="0.55"
        />
      </svg>
      <span
        style={{
          fontFamily: brand.font.display,
          fontWeight: brand.fontWeight.semibold,
          fontSize: brand.fontSize.xl,
          color: brand.color.text,
        }}
      >
        {brand.name}
      </span>
    </span>
  );
}
