import { Link, useParams } from "react-router-dom";
import { usePost } from "../lib/hooks";
import { errorMessage } from "../lib/errors";
import { CommentCount, CommentTree } from "../components/CommentTree";
import { CommentComposer } from "../components/Composer";
import { AuthorLine } from "../components/bits";
import { ErrorState, Spinner } from "../components/ui";

export function PostDetailPage() {
  const { id = "" } = useParams();
  const q = usePost(id);

  if (q.isLoading) return <Spinner label="Loading post…" />;
  if (q.isError) return <ErrorState message={errorMessage(q.error)} />;
  if (!q.data) return <ErrorState message="Not found." />;

  const post = q.data;
  return (
    <article className="mx-auto max-w-content">
      <Link to="/" className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-muted hover:text-text">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 18l-6-6 6-6" /></svg>
        Back to feed
      </Link>

      <div className="rounded-xl border border-border bg-surface p-6 shadow-card sm:p-8">
        <AuthorLine author={post.authorName} createdAt={post.createdAt} size={34} />
        <h1 className="mt-4 font-display text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
          {post.title}
        </h1>
        {post.imageUrl && (
          <img
            src={post.imageUrl}
            alt=""
            className="mt-5 w-full rounded-xl border border-border object-contain"
          />
        )}
        <div className="prose-body mt-5 whitespace-pre-wrap text-text">{post.body}</div>
      </div>

      <section className="mt-8">
        <h2 className="mb-4 font-display text-xl">
          <CommentCount postId={post.id} />
        </h2>
        <div className="mb-5 rounded-xl border border-border bg-surface p-4 shadow-card sm:p-5">
          <CommentComposer postId={post.id} />
        </div>
        <CommentTree postId={post.id} />
      </section>
    </article>
  );
}
