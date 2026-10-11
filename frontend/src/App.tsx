import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./pages/Layout";
import { HomePage, SearchPage } from "./pages/HomePage";
import { PostDetailPage } from "./pages/PostDetailPage";
import { AuthCallbackPage, CreatePostPage } from "./pages/CreatePostPage";
import { AuthPage } from "./pages/AuthPage";
import { EmptyState } from "./components/ui";

export function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/posts/:id" element={<PostDetailPage />} />
          <Route path="/new" element={<CreatePostPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/signin" element={<AuthPage mode="sign-in" />} />
          <Route path="/signup" element={<AuthPage mode="sign-up" />} />
          <Route path="/auth/callback" element={<AuthCallbackPage />} />
          <Route path="*" element={<EmptyState title="Page not found." />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
