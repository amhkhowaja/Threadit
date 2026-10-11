import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Logo } from "../components/Logo";
import { SearchBar, AuthMenu } from "../components/SearchBar";
import { RightRail } from "../components/RightRail";
import { Button } from "../components/ui";

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-20 border-b border-border bg-surface/85 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-shell items-center gap-4 px-4">
          <Link to="/" aria-label="Threadit home" className="shrink-0 transition-opacity hover:opacity-80">
            <Logo />
          </Link>

          <div className="flex flex-1 justify-center">
            <SearchBar />
          </div>

          <nav className="flex shrink-0 items-center gap-3">
            <Link to="/new">
              <Button variant="primary" className="hidden sm:inline-flex">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M12 5v14M5 12h14" /></svg>
                Create
              </Button>
            </Link>
            <span className="hidden h-6 w-px bg-border sm:block" aria-hidden />
            <AuthMenu />
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-shell px-4 py-6">{children}</main>
    </div>
  );
}

// Two-column content shell: main feed + right rail (rail hidden under lg).
export function ContentShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex gap-6">
      <div className="min-w-0 flex-1">{children}</div>
      <RightRail />
    </div>
  );
}
