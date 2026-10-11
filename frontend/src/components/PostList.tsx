import { Link } from "react-router-dom";
import { brand } from "../brand";
import type { PostFilter } from "../lib/hooks";
import { usePosts } from "../lib/hooks";
import type { PostResponse } from "../lib/api/types";
import { errorMessage } from "../lib/errors";
import { Button, EmptyState, ErrorState, Spinner } from "./ui";

function PostCard({ post }: { post: PostResponse }) {
  return (
    <article
      style={{
        background: brand.color.surface,
        border: `1px solid ${brand.color.border}`,
        borderRadius: brand.radius.md,
        padding: brand.space.md,
        marginBottom: brand.space.sm,
      }}
    >
      <h2 style={{ fontSize: brand.fontSize.lg }}>
        <Link to={`/posts/${post.id}`}>{post.title}</Link>
      </h2>
      <p style={{ color: brand.color.textMuted, margin: 0 }}>
        {post.body.length > 160 ? post.body.slice(0, 160) + "…" : post.body}
      </p>
      <p style={{ color: brand.color.textMuted, fontSize: brand.fontSize.xs, marginTop: brand.space.sm }}>
        {new Date(post.createdAt).toLocaleString()}
      </p>
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
        title={filter.search ? "No results." : "No posts yet."}
        hint={filter.search ? "Just-posted content can take a few seconds to appear in search." : "Be the first to post."}
      />
    );
  }

  return (
    <div>
      {posts.map((p) => (
        <PostCard key={p.id} post={p} />
      ))}
      {q.hasNextPage && (
        <div style={{ textAlign: "center", marginTop: brand.space.md }}>
          <Button variant="ghost" onClick={() => void q.fetchNextPage()} disabled={q.isFetchingNextPage}>
            {q.isFetchingNextPage ? "Loading…" : "Load more"}
          </Button>
        </div>
      )}
    </div>
  );
}
