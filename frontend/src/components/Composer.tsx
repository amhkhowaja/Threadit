import { useState } from "react";
import { brand } from "../brand";
import { config } from "../config";
import { useAttachImage, useCreateComment } from "../lib/hooks";
import { useAuth } from "../lib/auth/AuthProvider";
import { errorMessage } from "../lib/errors";
import { Button, ErrorState, Textarea } from "./ui";

export function CommentComposer({ postId }: { postId: string }) {
  const [text, setText] = useState("");
  const create = useCreateComment(postId);
  const { isAuthenticated, signIn } = useAuth();

  if (!isAuthenticated) {
    return (
      <p style={{ color: brand.color.textMuted }}>
        <button
          onClick={signIn}
          style={{ background: "none", border: "none", color: brand.color.accent, cursor: "pointer", padding: 0 }}
        >
          Sign in
        </button>{" "}
        to join the discussion.
      </p>
    );
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!text.trim()) return;
        create.mutate({ text, parentId: null }, { onSuccess: () => setText("") });
      }}
      style={{ marginBottom: brand.space.lg }}
    >
      <Textarea
        rows={3}
        value={text}
        maxLength={10000}
        placeholder="Add a comment…"
        onChange={(e) => setText(e.target.value)}
      />
      {create.isError && <ErrorState message={errorMessage(create.error)} />}
      <div style={{ marginTop: brand.space.xs }}>
        <Button type="submit" disabled={create.isPending}>
          {create.isPending ? "Posting…" : "Comment"}
        </Button>
      </div>
    </form>
  );
}

const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const ALLOWED = ["image/jpeg", "image/png", "image/webp", "image/gif"];

export function ImageUploader({ postId }: { postId: string }) {
  const upload = useAttachImage(postId);
  const [done, setDone] = useState<string | null>(null);
  const [local, setLocal] = useState<string | null>(null);

  if (!config.features.images) return null;

  return (
    <div style={{ marginTop: brand.space.sm }}>
      <input
        type="file"
        accept={ALLOWED.join(",")}
        onChange={(e) => {
          const file = e.target.files?.[0];
          setDone(null);
          setLocal(null);
          if (!file) return;
          if (!ALLOWED.includes(file.type)) return setLocal("Unsupported image type.");
          if (file.size > MAX_IMAGE_BYTES) return setLocal("Image exceeds 5 MB.");
          upload.mutate(file, { onSuccess: (key) => setDone(key) });
        }}
      />
      {upload.isPending && <p style={{ color: brand.color.textMuted }}>Uploading…</p>}
      {local && <ErrorState message={local} />}
      {upload.isError && <ErrorState message={errorMessage(upload.error)} />}
      {done && <p style={{ color: brand.color.textMuted, fontSize: brand.fontSize.xs }}>Attached: {done}</p>}
    </div>
  );
}
