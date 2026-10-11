import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { config } from "../config";
import { useAuth } from "../lib/auth/AuthProvider";
import { useCreatePost, useUploadDraftImage } from "../lib/hooks";
import { exchangeCode } from "../lib/auth/cognito";
import { errorMessage } from "../lib/errors";
import { Button, ErrorState, Input, Spinner, Textarea } from "../components/ui";

const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const ALLOWED = ["image/jpeg", "image/png", "image/webp", "image/gif"];

export function CreatePostPage() {
  const { isAuthenticated } = useAuth();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [imageKey, setImageKey] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [imgError, setImgError] = useState<string | null>(null);
  const create = useCreatePost();
  const upload = useUploadDraftImage();
  const navigate = useNavigate();

  if (!isAuthenticated) {
    return (
      <div className="mx-auto max-w-content rounded-xl border border-border bg-surface p-8 text-center shadow-card">
        <p className="text-muted">You need an account to create a post.</p>
        <Link to="/signin" className="mt-4 inline-block"><Button>Sign in</Button></Link>
      </div>
    );
  }

  const onPick = (file: File | undefined) => {
    setImgError(null);
    if (!file) return;
    if (!ALLOWED.includes(file.type)) return setImgError("Unsupported image type.");
    if (file.size > MAX_IMAGE_BYTES) return setImgError("Image exceeds 5 MB.");
    setPreview(URL.createObjectURL(file));
    upload.mutate(file, {
      onSuccess: (key) => setImageKey(key),
      onError: () => { setPreview(null); setImgError("Upload failed."); },
    });
  };

  return (
    <div className="mx-auto max-w-content rounded-xl border border-border bg-surface p-6 shadow-card sm:p-8">
      <h1 className="text-2xl">Create a post</h1>
      <form
        className="mt-5 space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate(
            { title, body, imageKey },
            { onSuccess: (post) => navigate(`/posts/${post.id}`) },
          );
        }}
      >
        <div>
          <label htmlFor="post-title" className="mb-1 block text-sm font-medium text-text">Title</label>
          <Input id="post-title" value={title} maxLength={300} required placeholder="An interesting title" onChange={(e) => setTitle(e.target.value)} />
          <p className="mt-1 text-right text-xs text-muted">{title.length}/300</p>
        </div>
        <div>
          <label htmlFor="post-body" className="mb-1 block text-sm font-medium text-text">Body</label>
          <Textarea id="post-body" rows={10} value={body} maxLength={40000} required placeholder="Share your thoughts…" onChange={(e) => setBody(e.target.value)} />
        </div>

        {config.features.images && (
          <div>
            <span className="mb-1 block text-sm font-medium text-text">Image (optional)</span>
            {preview ? (
              <div className="relative inline-block">
                <img src={preview} alt="Preview" className="max-h-64 rounded-lg border border-border" />
                <div className="mt-2 flex items-center gap-3 text-xs text-muted">
                  {upload.isPending ? "Uploading…" : imageKey ? "Attached ✓" : ""}
                  <button type="button" className="font-medium text-danger hover:underline" onClick={() => { setPreview(null); setImageKey(null); }}>
                    Remove
                  </button>
                </div>
              </div>
            ) : (
              <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-border bg-surface-2 px-4 py-3 text-sm text-muted hover:border-accent/40 hover:text-text">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15l-5-5L5 21" /><rect x="3" y="3" width="18" height="18" rx="2" /><circle cx="9" cy="9" r="2" /></svg>
                Attach an image
                <input type="file" accept={ALLOWED.join(",")} className="hidden" onChange={(e) => onPick(e.target.files?.[0])} />
              </label>
            )}
            {imgError && <div className="mt-2"><ErrorState message={imgError} /></div>}
          </div>
        )}

        {create.isError && <ErrorState message={errorMessage(create.error)} />}
        <div className="flex justify-end gap-2">
          <Link to="/"><Button type="button" variant="subtle">Cancel</Button></Link>
          <Button type="submit" disabled={create.isPending || upload.isPending}>
            {create.isPending ? "Publishing…" : "Publish"}
          </Button>
        </div>
      </form>
    </div>
  );
}

export function AuthCallbackPage() {
  const [params] = useSearchParams();
  const { setTokens } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = params.get("code");
    if (!code) return setError("Missing authorization code.");
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
