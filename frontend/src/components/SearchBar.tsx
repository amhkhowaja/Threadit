import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { brand } from "../brand";
import { config } from "../config";
import { useAuth } from "../lib/auth/AuthProvider";
import { Button, Input } from "./ui";

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
      style={{ display: "flex", gap: brand.space.sm, flex: 1, maxWidth: "320px" }}
    >
      <Input
        type="search"
        value={q}
        placeholder="Search posts…"
        aria-label="Search posts"
        onChange={(e) => setQ(e.target.value)}
      />
    </form>
  );
}

export function AuthMenu() {
  const { isAuthenticated, email, signIn, signOut } = useAuth();
  if (isAuthenticated) {
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: brand.space.sm }}>
        <span style={{ color: brand.color.textMuted, fontSize: brand.fontSize.sm }}>{email}</span>
        <Button variant="ghost" onClick={signOut}>
          Sign out
        </Button>
      </span>
    );
  }
  return <Button onClick={signIn}>Sign in</Button>;
}
