import { Link } from "react-router-dom";
import { brand } from "../brand";
import { Button } from "./ui";

export function AboutCard() {
  return (
    <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
      <h3 className="font-display text-lg">About {brand.name}</h3>
      <p className="mt-2 text-sm leading-relaxed text-muted">
        A threaded message board. Create a post, read the discussion, and reply to any
        comment — replies nest up to eight levels deep.
      </p>
      <Link to="/new" className="mt-4 block">
        <Button className="w-full">Create a post</Button>
      </Link>
    </div>
  );
}

export function GuidelinesCard() {
  const items = [
    "Reply in-thread to keep context",
    "Keep titles clear and specific",
    "Reads are open to everyone; posting needs an account",
  ];
  return (
    <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
      <h3 className="font-display text-lg">Good to know</h3>
      <ul className="mt-2 space-y-2 text-sm text-muted">
        {items.map((t) => (
          <li key={t} className="flex gap-2">
            <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
            {t}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function RightRail() {
  return (
    <aside className="hidden w-80 shrink-0 space-y-4 lg:block">
      <div className="sticky top-20 space-y-4">
        <AboutCard />
        <GuidelinesCard />
        <p className="px-1 text-xs text-muted">
          © {new Date().getFullYear()} {brand.name}
        </p>
      </div>
    </aside>
  );
}
