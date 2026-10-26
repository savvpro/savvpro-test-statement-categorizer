import { test, expect } from "@playwright/test";

test("import, explain, review, persist, duplicate import, export and mobile layout", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByText("A fresh start for your statements"),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/desktop-welcome.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Try sample data" }).click();
  await expect(
    page.getByText("28 transactions imported. Your statement is ready."),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Where it all goes" }),
  ).toBeVisible();
  await expect(page.getByText("07", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Review JOES CAFE 9921", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(
    page.getByText("No reliable rule matched.", { exact: false }).first(),
  ).toBeVisible();
  await page
    .getByRole("combobox", { name: "Category", exact: true })
    .selectOption("Meals");
  await page
    .getByLabel("Note", { exact: false })
    .fill("Fictional client meeting");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByRole("button", { name: "Reviewed", exact: true }).click();
  await expect(
    page.getByRole("row").filter({ hasText: "JOES CAFE" }),
  ).toContainText("Meals");
  await page.reload();
  await page
    .getByRole("button", { name: "Review JOES CAFE 9921", exact: true })
    .click();
  await expect(page.getByLabel("Note", { exact: false })).toHaveValue(
    "Fictional client meeting",
  );
  await page.keyboard.press("Escape");
  await page
    .getByRole("button", { name: "Upload statement", exact: true })
    .click();
  await page.getByRole("button", { name: "Try sample data" }).click();
  await expect(
    page.getByText("Already imported. Your saved reviews are still here."),
  ).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "Export CSV", exact: true }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/^ledgerly-.*\.csv$/);
  await page.getByRole("button", { name: "Let’s review them" }).click();
  await expect(
    page.getByRole("row").filter({ hasText: "JOES CAFE" }),
  ).toHaveCount(0);
  await page.getByLabel("Search transactions").fill("UNKNOWN MERCHANT");
  await expect(
    page.getByRole("row").filter({ hasText: "UNKNOWN MERCHANT" }),
  ).toBeVisible();
  await page.getByLabel("Search transactions").fill("nonexistentmerchant");
  await expect(
    page.getByRole("heading", { name: "No matching transactions" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Clear filters" }).click();
  const notification = page.getByRole("button", {
    name: "Dismiss notification",
  });
  if (await notification.isVisible()) await notification.click();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "test-results/desktop-transactions.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Overview", exact: true }).click();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "test-results/desktop-overview.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "test-results/mobile-overview.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page
    .getByRole("button", { name: "Review JOES CAFE 9921", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.screenshot({
    path: "test-results/mobile-review.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("invalid CSV shows a row error and does not create a statement", async ({
  page,
  request,
}) => {
  const before = await (await request.get("/api/statements")).json();
  await page.goto("/");
  await page
    .getByRole("button", { name: "Upload statement", exact: true })
    .click();
  await page.getByLabel("Choose CSV statement").setInputFiles({
    name: "bad.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "date,description,amount\n2026-02-30,FAKE MERCHANT,-10",
    ),
  });
  await page
    .getByRole("button", { name: "Import statement", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("Row 2");
  const after = await (await request.get("/api/statements")).json();
  expect(after.length).toBe(before.length);
});
