import { brand } from "../brand";

export function Logo({ size = 26 }: { size?: number }) {
  return (
    <span className="inline-flex items-center gap-2">
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M6 4v9a3 3 0 0 0 3 3h6" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" />
        <circle cx="6" cy="4" r="2.4" fill="var(--accent)" />
        <circle cx="15" cy="16" r="2.4" fill="var(--accent)" />
        <circle cx="18" cy="9" r="2" fill="var(--accent)" opacity="0.55" />
        <path d="M6 9h7" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" opacity="0.55" />
      </svg>
      <span className="font-display text-xl font-semibold tracking-tight text-text">{brand.name}</span>
    </span>
  );
}
