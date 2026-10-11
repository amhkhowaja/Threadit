import type { ButtonHTMLAttributes, InputHTMLAttributes, TextareaHTMLAttributes } from "react";
import { brand } from "../brand";

export function Button({
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" }) {
  const base = {
    font: brand.font.text,
    padding: `${brand.space.sm} ${brand.space.md}`,
    borderRadius: brand.radius.md,
    fontWeight: brand.fontWeight.medium,
    fontSize: brand.fontSize.sm,
    cursor: props.disabled ? "not-allowed" : "pointer",
    opacity: props.disabled ? 0.6 : 1,
    border: `1px solid ${variant === "primary" ? brand.color.accent : brand.color.border}`,
    background: variant === "primary" ? brand.color.accent : "transparent",
    color: variant === "primary" ? "#fff" : brand.color.text,
  } as const;
  return <button {...props} style={{ ...base, ...(props.style ?? {}) }} />;
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} style={{ ...fieldStyle, ...(props.style ?? {}) }} />;
}

export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} style={{ ...fieldStyle, resize: "vertical", ...(props.style ?? {}) }} />;
}

const fieldStyle = {
  width: "100%",
  padding: brand.space.sm,
  borderRadius: brand.radius.md,
  border: `1px solid ${brand.color.border}`,
  fontFamily: brand.font.text,
  fontSize: brand.fontSize.base,
  background: brand.color.surface,
  color: brand.color.text,
} as const;

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <p role="status" style={{ color: brand.color.textMuted, padding: brand.space.md }}>
      {label}
    </p>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div style={{ textAlign: "center", padding: brand.space.xl, color: brand.color.textMuted }}>
      <p style={{ fontWeight: brand.fontWeight.medium, color: brand.color.text }}>{title}</p>
      {hint && <p style={{ fontSize: brand.fontSize.sm }}>{hint}</p>}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div
      role="alert"
      style={{
        background: brand.color.dangerSoft,
        color: brand.color.danger,
        padding: brand.space.md,
        borderRadius: brand.radius.md,
        fontSize: brand.fontSize.sm,
      }}
    >
      {message}
    </div>
  );
}
