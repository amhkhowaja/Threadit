import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { brand } from "../brand";
import { Logo } from "../components/Logo";
import { SearchBar, AuthMenu } from "../components/SearchBar";
import { Button } from "../components/ui";

export function Layout({ children }: { children: ReactNode }) {
  return (
    <>
      <header
        style={{
          borderBottom: `1px solid ${brand.color.border}`,
          background: brand.color.surface,
          position: "sticky",
          top: 0,
        }}
      >
        <div
          style={{
            maxWidth: brand.layout.maxWidth,
            margin: "0 auto",
            padding: `${brand.space.sm} ${brand.space.md}`,
            display: "flex",
            alignItems: "center",
            gap: brand.space.md,
          }}
        >
          <Link to="/" aria-label="Threadit home">
            <Logo />
          </Link>
          <SearchBar />
          <nav style={{ marginLeft: "auto", display: "flex", gap: brand.space.sm, alignItems: "center" }}>
            <Link to="/new">
              <Button variant="ghost">New post</Button>
            </Link>
            <AuthMenu />
          </nav>
        </div>
      </header>
      <main
        style={{
          maxWidth: brand.layout.maxWidth,
          margin: "0 auto",
          padding: `${brand.space.lg} ${brand.space.md}`,
        }}
      >
        {children}
      </main>
    </>
  );
}
