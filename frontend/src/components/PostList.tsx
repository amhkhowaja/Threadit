import { Link } from "react-router-dom";
import type { PostFilter } from "../lib/hooks";
import { usePosts } from "../lib/hooks";
import type { PostResponse } from "../lib/api/types";
import { errorMessage } from "../lib/errors";
import { Button, EmptyState, ErrorState, Spinner } from "./ui";
import { AuthorLine } from "./bits";

function PostCard({ post }: { post: PostResponse }) {
  return (
    <article className="rounded-xl border border-border bg-surface p-5 shadow-card transition-all duration-150 hover:border-accent/40 hover:shadow-lift sm:p-6">
      <AuthorLine author={post.authorName} createdAt={post.createdAt} />
      <h2 className="mt-3 font-display text-2xl font-semibold leading-tight tracking-tight">
        <Link to={`/posts/${post.id}`} className="text-text hover:text-accent">
          {post.title}
        </Link>
      </h2>
      {post.body && (
        <p className="clamp-3 mt-2 text-[15px] leading-relaxed text-muted">{post.body}</p>
      )}
      {post.imageUrl && (
        <Link to={`/posts/${post.id}`} className="mt-3 block">
          <img
            src={post.imageUrl}
            alt=""
            loading="lazy"
            className="max-h-80 w-full rounded-lg border border-border object-cover"
          />
        </Link>
      )}
      <div className="mt-4 flex items-center gap-3 border-t border-border/60 pt-3">
        <Link
          to={`/posts/${post.id}`}
          className="inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium text-muted transition-colors hover:bg-surface-2 hover:text-text"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8z" /></svg>
          View discussion
        </Link>
      </div>
    </article>
  );
}

export function PostList({ filter = {} }: { filter?: PostFilter }) {
  const q = usePosts(filter);

  if (q.isLoading) return <Spinner label="Loading posts…" />;
  if (q.isError) return <ErrorState message={errorMessage(q.error)} />;

  const posts = q.data?.pages.flatMap((p) => p.items) ?? [];
  if (posts.length === 0) {
    return (
      <EmptyState
        title={filter.search ? "No results found." : "No posts yet."}
        hint={
          filter.search
            ? "Just-posted content can take a few seconds to appear in search."
            : "Start the conversation — create the first post."
        }
      />
    );
  }

  return (
    <div className="space-y-4">
      {posts.map((p) => (
        <PostCard key={p.id} post={p} />
      ))}
      {q.hasNextPage && (
        <div className="pt-2 text-center">
          <Button variant="ghost" onClick={() => void q.fetchNextPage()} disabled={q.isFetchingNextPage}>
            {q.isFetchingNextPage ? "Loading…" : "Load more"}
          </Button>
        </div>
      )}
    </div>
  );
}
