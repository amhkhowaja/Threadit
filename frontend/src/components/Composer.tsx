import { useState } from "react";
import { useCreateComment } from "../lib/hooks";
import { useAuth } from "../lib/auth/AuthProvider";
import { errorMessage } from "../lib/errors";
import { Button, ErrorState, Textarea } from "./ui";

export function CommentComposer({ postId }: { postId: string }) {
  const [text, setText] = useState("");
  const create = useCreateComment(postId);
  const { isAuthenticated, signIn } = useAuth();

  if (!isAuthenticated) {
    return (
      <div className="rounded-lg border border-border bg-surface-2 px-4 py-3 text-sm text-muted">
        <button onClick={signIn} className="font-medium text-accent hover:text-accent-hover">
          Sign in
        </button>{" "}
        to join the discussion.
      </div>
    );
  }

  const submit = () => {
    if (!text.trim()) return;
    create.mutate({ text, parentId: null }, { onSuccess: () => setText("") });
  };

  return (
    <form onSubmit={(e) => { e.preventDefault(); submit(); }} className="space-y-2">
      <Textarea
        rows={3}
        value={text}
        maxLength={10000}
        placeholder="Add a comment…  (Enter to post, Shift+Enter for a new line)"
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
      />
      {create.isError && <ErrorState message={errorMessage(create.error)} />}
      <div className="flex justify-end">
        <Button type="submit" disabled={create.isPending}>{create.isPending ? "Posting…" : "Comment"}</Button>
      </div>
    </form>
  );
}
