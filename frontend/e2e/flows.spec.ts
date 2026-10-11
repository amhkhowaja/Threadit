import { expect, test } from "@playwright/test";

// Runs against the local dev stack (Floci + services + vite) in dev-auth mode.
const stamp = () => Date.now().toString().slice(-6);

test("feed loads and shows the app shell", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("link", { name: "Threadit home" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Create/i }).first()).toBeVisible();
});

test("create a post, open it, comment and reply", async ({ page }) => {
  const title = `E2E post ${stamp()}`;
  const comment = `E2E comment ${stamp()}`;
  const reply = `E2E reply ${stamp()}`;

  // Create
  await page.goto("/new");
  await page.getByLabel("Title").fill(title);
  await page.getByLabel("Body").fill("Body written by the Playwright end-to-end test.");
  await page.getByRole("button", { name: "Publish" }).click();

  // Navigates straight to the new post
  await expect(page.getByRole("heading", { name: title })).toBeVisible();

  // Comment (click Comment button)
  await page.getByPlaceholder(/Add a comment/i).fill(comment);
  await page.getByRole("button", { name: "Comment" }).click();
  await expect(page.getByText(comment)).toBeVisible();

  // Reply to the comment
  await page.getByRole("button", { name: "Reply" }).first().click();
  const replyBox = page.getByPlaceholder(/Write a reply/i);
  await replyBox.fill(reply);
  await replyBox.press("Enter");
  await expect(page.getByText(reply)).toBeVisible();
});

test("post page shows no fake vote/share widgets", async ({ page }) => {
  await page.goto("/");
  await page.locator("article a").first().click();
  await expect(page.getByRole("button", { name: /upvote/i })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /share/i })).toHaveCount(0);
});

test("attach an image during compose and it renders on the post", async ({ page }) => {
  const title = `E2E image post ${stamp()}`;
  // a tiny valid PNG
  const png = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "base64",
  );
  await page.goto("/new");
  await page.getByLabel("Title").fill(title);
  await page.getByLabel("Body").fill("This post has an image attached during compose.");
  await page.setInputFiles('input[type="file"]', {
    name: "pixel.png",
    mimeType: "image/png",
    buffer: png,
  });
  await expect(page.getByText("Attached ✓")).toBeVisible({ timeout: 15000 });
  await page.getByRole("button", { name: "Publish" }).click();

  // On the post page, the image should render.
  await expect(page.getByRole("heading", { name: title })).toBeVisible();
  const img = page.locator("article img");
  await expect(img.first()).toBeVisible();
  // image actually loads (naturalWidth > 0)
  await expect
    .poll(async () => img.first().evaluate((el: HTMLImageElement) => el.naturalWidth))
    .toBeGreaterThan(0);
});
