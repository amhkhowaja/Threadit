import { Link } from "react-router-dom";
import { brand } from "../brand";
import { config } from "../config";
import { useAuth } from "../lib/auth/AuthProvider";
import { Logo } from "../components/Logo";
import { Button } from "../components/ui";

const POINTS = [
  "Follow threaded discussions, not flat comment walls.",
  "Post, reply at any depth, and keep the conversation organized.",
  "Minimal, fast, distraction-free.",
];

export function AuthPage({ mode = "sign-in" }: { mode?: "sign-in" | "sign-up" }) {
  const { signIn, isAuthenticated } = useAuth();
  const devMode = Boolean(config.devUserId);
  const isSignUp = mode === "sign-up";

  return (
    <div className="mx-auto grid max-w-4xl gap-8 py-6 md:grid-cols-2 md:items-center">
      {/* Brand / value panel */}
      <section className="rounded-xl border border-border bg-surface-2 p-8">
        <Logo size={34} />
        <p className="mt-4 font-display text-2xl leading-tight">{brand.tagline}</p>
        <ul className="mt-6 space-y-3">
          {POINTS.map((p) => (
            <li key={p} className="flex items-start gap-2.5 text-sm text-muted">
              <svg className="mt-0.5 shrink-0 text-accent" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 6L9 17l-5-5" /></svg>
              {p}
            </li>
          ))}
        </ul>
      </section>

      {/* Action panel */}
      <section className="rounded-xl border border-border bg-surface p-8 shadow-card">
        <h1 className="text-xl">{isSignUp ? "Create your account" : "Welcome back"}</h1>
        <p className="mt-1 text-sm text-muted">
          {isSignUp ? "Join Threadit to post and reply." : "Sign in to post, reply, and vote."}
        </p>

        {isAuthenticated ? (
          <div className="mt-6 rounded-md border border-accent/20 bg-accent-soft px-4 py-3 text-sm text-text">
            You're signed in.{" "}
            <Link to="/" className="font-medium text-accent hover:text-accent-hover">Go to feed →</Link>
          </div>
        ) : devMode ? (
          <div className="mt-6 space-y-4">
            <div className="rounded-md border border-border bg-surface-2 px-4 py-3 text-sm text-muted">
              Local dev mode — authentication is stubbed; you're already acting as a dev user.
            </div>
            <Link to="/">
              <Button className="w-full">Continue to feed</Button>
            </Link>
          </div>
        ) : (
          <div className="mt-6 space-y-4">
            <Button className="w-full" onClick={signIn}>
              {isSignUp ? "Sign up with Cognito" : "Continue with Cognito"}
            </Button>
            <p className="text-center text-xs text-muted">
              Secured by Amazon Cognito. We never see your password.
            </p>
          </div>
        )}

        <p className="mt-6 border-t border-border pt-4 text-center text-sm text-muted">
          {isSignUp ? (
            <>Already have an account? <Link to="/signin" className="font-medium text-accent">Sign in</Link></>
          ) : (
            <>New to Threadit? <Link to="/signup" className="font-medium text-accent">Create an account</Link></>
          )}
        </p>
      </section>
    </div>
  );
}
