import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { brand } from "../brand";
import { useAuth } from "../lib/auth/AuthProvider";
import { useCreatePost } from "../lib/hooks";
import { exchangeCode } from "../lib/auth/cognito";
import { errorMessage } from "../lib/errors";
import { Button, ErrorState, Input, Spinner, Textarea } from "../components/ui";

export function CreatePostPage() {
  const { isAuthenticated, signIn } = useAuth();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const create = useCreatePost();
  const navigate = useNavigate();

  if (!isAuthenticated) {
    return (
      <div style={{ textAlign: "center", padding: brand.space.xl }}>
        <p>You need to sign in to create a post.</p>
        <Button onClick={signIn}>Sign in</Button>
      </div>
    );
  }

  return (
    <>
      <h1 style={{ fontSize: brand.fontSize.xl }}>New post</h1>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate(
            { title, body },
            { onSuccess: (post) => navigate(`/posts/${post.id}`) },
          );
        }}
      >
        <label>
          <span style={{ fontSize: brand.fontSize.sm }}>Title</span>
          <Input
            value={title}
            maxLength={300}
            required
            onChange={(e) => setTitle(e.target.value)}
            style={{ marginBottom: brand.space.md }}
          />
        </label>
        <label>
          <span style={{ fontSize: brand.fontSize.sm }}>Body</span>
          <Textarea
            rows={10}
            value={body}
            maxLength={40000}
            required
            onChange={(e) => setBody(e.target.value)}
            style={{ marginBottom: brand.space.md }}
          />
        </label>
        {create.isError && <ErrorState message={errorMessage(create.error)} />}
        <Button type="submit" disabled={create.isPending}>
          {create.isPending ? "Publishing…" : "Publish"}
        </Button>
      </form>
    </>
  );
}

export function AuthCallbackPage() {
  const [params] = useSearchParams();
  const { setTokens } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = params.get("code");
    if (!code) {
      setError("Missing authorization code.");
      return;
    }
    exchangeCode(code)
      .then((tokens) => {
        setTokens(tokens);
        navigate("/", { replace: true });
      })
      .catch((e) => setError(errorMessage(e)));
  }, [params, setTokens, navigate]);

  if (error) return <ErrorState message={error} />;
  return <Spinner label="Signing you in…" />;
}
