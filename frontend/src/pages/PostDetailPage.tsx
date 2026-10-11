import { useParams } from "react-router-dom";
import { brand } from "../brand";
import { usePost } from "../lib/hooks";
import { errorMessage } from "../lib/errors";
import { CommentTree } from "../components/CommentTree";
import { CommentComposer, ImageUploader } from "../components/Composer";
import { ErrorState, Spinner } from "../components/ui";

export function PostDetailPage() {
  const { id = "" } = useParams();
  const q = usePost(id);

  if (q.isLoading) return <Spinner label="Loading post…" />;
  if (q.isError) return <ErrorState message={errorMessage(q.error)} />;
  if (!q.data) return <ErrorState message="Not found." />;

  const post = q.data;
  return (
    <article>
      <h1 style={{ fontSize: brand.fontSize["2xl"] }}>{post.title}</h1>
      <p style={{ color: brand.color.textMuted, fontSize: brand.fontSize.xs }}>
        {new Date(post.createdAt).toLocaleString()}
      </p>
      <p style={{ whiteSpace: "pre-wrap", marginBottom: brand.space.lg }}>{post.body}</p>
      <ImageUploader postId={post.id} />

      <h2 style={{ fontSize: brand.fontSize.lg, marginTop: brand.space.xl }}>Comments</h2>
      <CommentComposer postId={post.id} />
      <CommentTree postId={post.id} />
    </article>
  );
}
