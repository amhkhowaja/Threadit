import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  TextareaHTMLAttributes,
} from "react";

type Variant = "primary" | "ghost" | "subtle";

const variants: Record<Variant, string> = {
  primary:
    "bg-accent text-white border border-accent hover:bg-accent-hover shadow-sm",
  ghost:
    "bg-transparent text-text border border-border hover:bg-surface-2",
  subtle: "bg-surface-2 text-text border border-transparent hover:bg-border/40",
};

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-2 rounded-md px-3.5 py-2 text-sm font-medium transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed ${variants[variant]} ${className}`}
    />
  );
}

const field =
  "w-full rounded-md border border-border bg-surface px-3 py-2 text-text placeholder:text-muted/70 focus:border-accent focus:ring-2 focus:ring-accent/20 outline-none transition";

export function Input({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${field} ${className}`} />;
}

export function Textarea({ className = "", ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={`${field} resize-y leading-relaxed ${className}`} />;
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 py-8 text-muted">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-border border-t-accent" />
      {label}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-surface-2 px-6 py-12 text-center">
      <p className="font-medium text-text">{title}</p>
      {hint && <p className="mt-1 text-sm text-muted">{hint}</p>}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="rounded-md border border-danger/20 bg-danger-soft px-3 py-2 text-sm text-danger"
    >
      {message}
    </div>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-lg border border-border bg-surface shadow-card transition-shadow hover:shadow-lift ${className}`}
    >
      {children}
    </div>
  );
}
