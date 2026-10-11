import { avatarColor, initials, relativeTime } from "../lib/format";

export function Avatar({ name, size = 28 }: { name: string; size?: number }) {
  return (
    <span
      aria-hidden="true"
      className="inline-flex shrink-0 items-center justify-center rounded-full font-semibold text-white"
      style={{ width: size, height: size, background: avatarColor(name), fontSize: size * 0.4 }}
    >
      {initials(name)}
    </span>
  );
}

export function AuthorLine({
  author,
  createdAt,
  size = 28,
}: {
  author: string;
  createdAt: string;
  size?: number;
}) {
  return (
    <div className="flex items-center gap-2.5">
      <Avatar name={author} size={size} />
      <div className="flex flex-col leading-tight">
        <span className="text-sm font-semibold text-text">{author}</span>
        <time className="text-xs text-muted">{relativeTime(createdAt)}</time>
      </div>
    </div>
  );
}
