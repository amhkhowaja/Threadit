import { useSearchParams } from "react-router-dom";
import { brand } from "../brand";
import { PostList } from "../components/PostList";

export function HomePage() {
  return (
    <>
      <h1 style={{ fontSize: brand.fontSize["2xl"] }}>Latest</h1>
      <PostList />
    </>
  );
}

export function SearchPage() {
  const [params] = useSearchParams();
  const q = params.get("q") ?? "";
  return (
    <>
      <h1 style={{ fontSize: brand.fontSize.xl }}>
        Results for “{q}”
      </h1>
      <PostList filter={{ search: q }} />
    </>
  );
}
