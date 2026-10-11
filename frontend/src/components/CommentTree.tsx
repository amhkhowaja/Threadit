import { useState } from "react";
import { brand } from "../brand";
import type { CommentResponse } from "../lib/api/types";
import { useComments, useCreateComment } from "../lib/hooks";
import { useAuth } from "../lib/auth/AuthProvider";
import { errorMessage } from "../lib/errors";
import { Button, ErrorState, Spinner, Textarea } from "./ui";

const MAX_DEPTH = 8;

interface TreeNode {
  comment: CommentResponse;
  children: TreeNode[];
}

function buildTree(items: CommentResponse[]): TreeNode[] {
  const byId = new Map<string, TreeNode>();
  const roots: TreeNode[] = [];
  for (const c of items) byId.set(c.id, { comment: c, children: [] });
  for (const c of items) {
    const node = byId.get(c.id)!;
    if (c.parentId && byId.has(c.parentId)) byId.get(c.parentId)!.children.push(node);
    else roots.push(node);
  }
  return roots;
}

function ReplyBox({ postId, parentId, onDone }: { postId: string; parentId: string; onDone: () => void }) {
  const [text, setText] = useState("");
  const create = useCreateComment(postId);
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!text.trim()) return;
        create.mutate({ text, parentId }, { onSuccess: () => { setText(""); onDone(); } });
      }}
      style={{ marginTop: brand.space.sm }}
    >
      <Textarea
        rows={2}
        value={text}
        maxLength={10000}
        placeholder="Write a reply…"
        onChange={(e) => setText(e.target.value)}
      />
      {create.isError && <ErrorState message={errorMessage(create.error)} />}
      <div style={{ display: "flex", gap: brand.space.sm, marginTop: brand.space.xs }}>
        <Button type="submit" disabled={create.isPending}>
          {create.isPending ? "Replying…" : "Reply"}
        </Button>
        <Button type="button" variant="ghost" onClick={onDone}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

function Node({ node, postId }: { node: TreeNode; postId: string }) {
  const [replying, setReplying] = useState(false);
  const { isAuthenticated, signIn } = useAuth();
  const c = node.comment;
  const atCap = c.depth >= MAX_DEPTH - 1;

  return (
    <li style={{ listStyle: "none" }}>
      <div
        style={{
          borderLeft: `2px solid ${brand.color.border}`,
          paddingLeft: brand.space.md,
          marginTop: brand.space.sm,
        }}
      >
        <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{c.text}</p>
        <p style={{ fontSize: brand.fontSize.xs, color: brand.color.textMuted, margin: `${brand.space.xs} 0` }}>
          {new Date(c.createdAt).toLocaleString()}
          {!atCap && (
            <>
              {" · "}
              <button
                onClick={() => (isAuthenticated ? setReplying((v) => !v) : signIn())}
                style={{ background: "none", border: "none", color: brand.color.accent, cursor: "pointer", padding: 0 }}
              >
                reply
              </button>
            </>
          )}
          {atCap && <span> · continue this thread as a new reply</span>}
        </p>
        {replying && <ReplyBox postId={postId} parentId={c.id} onDone={() => setReplying(false)} />}
        {node.children.length > 0 && (
          <ul style={{ padding: 0, margin: 0 }}>
            {node.children.map((child) => (
              <Node key={child.comment.id} node={child} postId={postId} />
            ))}
          </ul>
        )}
      </div>
    </li>
  );
}

export function CommentTree({ postId }: { postId: string }) {
  const q = useComments(postId);
  if (q.isLoading) return <Spinner label="Loading comments…" />;
  if (q.isError) return <ErrorState message={errorMessage(q.error)} />;

  const items = q.data?.pages.flatMap((p) => p.items) ?? [];
  if (items.length === 0) return <p style={{ color: brand.color.textMuted }}>No comments yet.</p>;

  const tree = buildTree(items);
  return (
    <ul style={{ padding: 0, margin: 0 }}>
      {tree.map((n) => (
        <Node key={n.comment.id} node={n} postId={postId} />
      ))}
      {q.hasNextPage && (
        <Button variant="ghost" onClick={() => void q.fetchNextPage()} disabled={q.isFetchingNextPage}>
          {q.isFetchingNextPage ? "Loading…" : "Load more comments"}
        </Button>
      )}
    </ul>
  );
}
