import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { config } from "../config";
import { useAuth } from "../lib/auth/AuthProvider";
import { useMe } from "../lib/hooks";
import { Avatar } from "./bits";
import { Button } from "./ui";

export function SearchBar() {
  const [q, setQ] = useState("");
  const navigate = useNavigate();
  if (!config.features.search) return null;
  return (
    <form
      role="search"
      onSubmit={(e) => {
        e.preventDefault();
        if (q.trim()) navigate(`/search?q=${encodeURIComponent(q.trim())}`);
      }}
      className="relative flex-1 max-w-md"
    >
      <svg className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" /></svg>
      <input
        type="search"
        value={q}
        placeholder="Search Threadit"
        aria-label="Search posts"
        onChange={(e) => setQ(e.target.value)}
        className="w-full rounded-full border border-border bg-surface-2 py-2 pl-9 pr-4 text-sm outline-none transition focus:border-accent focus:bg-surface focus:ring-2 focus:ring-accent/20"
      />
    </form>
  );
}

export function AuthMenu() {
  const { isAuthenticated, signIn, signOut } = useAuth();
  const me = useMe(isAuthenticated);
  if (isAuthenticated) {
    const name = me.data?.authorName ?? "…";
    return (
      <div className="flex items-center gap-2.5">
        <Avatar name={name} size={28} />
        <span className="hidden text-sm font-medium text-text sm:inline">{name}</span>
        <Button variant="ghost" onClick={signOut}>Sign out</Button>
      </div>
    );
  }
  return <Button onClick={signIn}>Sign in</Button>;
}
