import { useState } from "react";
import type { CommentResponse } from "../lib/api/types";
import { useComments, useCreateComment } from "../lib/hooks";
import { useAuth } from "../lib/auth/AuthProvider";
import { errorMessage } from "../lib/errors";
import { Button, ErrorState, Spinner, Textarea } from "./ui";
import { AuthorLine } from "./bits";

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
  const submit = () => {
    if (!text.trim()) return;
    create.mutate({ text, parentId }, { onSuccess: () => { setText(""); onDone(); } });
  };
  return (
    <form onSubmit={(e) => { e.preventDefault(); submit(); }} className="mt-3 space-y-2">
      <Textarea
        rows={3}
        value={text}
        maxLength={10000}
        placeholder="Write a reply…  (Enter to reply, Shift+Enter for a new line)"
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
        autoFocus
      />
      {create.isError && <ErrorState message={errorMessage(create.error)} />}
      <div className="flex gap-2">
        <Button type="submit" disabled={create.isPending}>{create.isPending ? "Replying…" : "Reply"}</Button>
        <Button type="button" variant="subtle" onClick={onDone}>Cancel</Button>
      </div>
    </form>
  );
}

function Node({ node, postId }: { node: TreeNode; postId: string }) {
  const [replying, setReplying] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const { isAuthenticated, signIn } = useAuth();
  const c = node.comment;
  const atCap = c.depth >= MAX_DEPTH - 1;
  const childCount = node.children.length;

  return (
    <li className="list-none">
      <div className="rounded-xl border border-border bg-surface p-4 shadow-card">
        <div className="flex items-center justify-between">
          <AuthorLine author={c.authorName} createdAt={c.createdAt} size={30} />
          {childCount > 0 && (
            <button
              onClick={() => setCollapsed((v) => !v)}
              className="rounded-md px-2 py-1 text-xs font-medium text-muted hover:bg-surface-2 hover:text-text"
            >
              {collapsed ? `Show ${childCount} ${childCount === 1 ? "reply" : "replies"}` : "Collapse"}
            </button>
          )}
        </div>
        <p className="mt-2.5 whitespace-pre-wrap text-[15px] leading-relaxed text-text">{c.text}</p>
        <div className="mt-3">
          {!atCap ? (
            <button
              onClick={() => (isAuthenticated ? setReplying((v) => !v) : signIn())}
              className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium text-muted transition-colors hover:bg-surface-2 hover:text-text"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 10h11a4 4 0 0 1 0 8h-1M3 10l4-4M3 10l4 4" /></svg>
              Reply
            </button>
          ) : (
            <span className="text-xs italic text-muted">Max depth reached — continue as a new top-level reply.</span>
          )}
        </div>
        {replying && <ReplyBox postId={postId} parentId={c.id} onDone={() => setReplying(false)} />}
      </div>

      {!collapsed && childCount > 0 && (
        <ul className="mt-3 space-y-3 border-l-2 border-border pl-4 sm:pl-5">
          {node.children.map((child) => (
            <Node key={child.comment.id} node={child} postId={postId} />
          ))}
        </ul>
      )}
    </li>
  );
}

export function CommentTree({ postId }: { postId: string }) {
  const q = useComments(postId);
  if (q.isLoading) return <Spinner label="Loading comments…" />;
  if (q.isError) return <ErrorState message={errorMessage(q.error)} />;

  const items = q.data?.pages.flatMap((p) => p.items) ?? [];
  if (items.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border bg-surface-2 px-6 py-10 text-center">
        <p className="font-medium text-text">No comments yet</p>
        <p className="mt-1 text-sm text-muted">Be the first to share your thoughts.</p>
      </div>
    );
  }

  const tree = buildTree(items);
  return (
    <ul className="space-y-3">
      {tree.map((n) => (
        <Node key={n.comment.id} node={n} postId={postId} />
      ))}
      {q.hasNextPage && (
        <div className="pt-1">
          <Button variant="ghost" onClick={() => void q.fetchNextPage()} disabled={q.isFetchingNextPage}>
            {q.isFetchingNextPage ? "Loading…" : "Load more comments"}
          </Button>
        </div>
      )}
    </ul>
  );
}

export function CommentCount({ postId }: { postId: string }) {
  const q = useComments(postId);
  const n = q.data?.pages.flatMap((p) => p.items).length ?? 0;
  return <>{n > 0 ? `${n}${q.hasNextPage ? "+" : ""} comments` : "Comments"}</>;
}
