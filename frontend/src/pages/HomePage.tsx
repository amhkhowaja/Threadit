import { useSearchParams } from "react-router-dom";
import { PostList } from "../components/PostList";
import { ContentShell } from "./Layout";

export function HomePage() {
  return (
    <ContentShell>
      <div className="mb-4 flex items-baseline justify-between">
        <h1 className="text-2xl">Latest</h1>
        <span className="text-xs font-medium uppercase tracking-wide text-muted">Newest first</span>
      </div>
      <PostList />
    </ContentShell>
  );
}

export function SearchPage() {
  const [params] = useSearchParams();
  const q = params.get("q") ?? "";
  return (
    <ContentShell>
      <h1 className="mb-4 text-xl">
        Results for <span className="text-accent">“{q}”</span>
      </h1>
      <PostList filter={{ search: q }} />
    </ContentShell>
  );
}
