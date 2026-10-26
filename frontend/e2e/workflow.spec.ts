import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

test.beforeEach(async ({ request }) => {
  // Test-owned server/database only. Keep cases independent, without mocking the API.
  const statements = await (await request.get("/api/statements")).json();
  for (const statement of statements)
    await request.delete(`/api/statements/${statement.id}`);
});

test("import → explain → review → persisted history → draft export", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await page.getByRole("button", { name: "Try a sample statement" }).click();
  await expect(page.getByText("$182.48", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: /Review JOES CAFE/ }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByText(/No sufficiently specific rule/)).toBeVisible();
  await page
    .getByRole("combobox", { name: "Category", exact: true })
    .selectOption("Meals");
  await page
    .getByLabel(/Review note/)
    .fill("Client meeting; fictional receipt verified.");
  await page.getByRole("button", { name: "Save decision" }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(page.getByText("$200.88", { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText("$200.88", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Review history" }).click();
  await expect(
    page.getByText("Client meeting; fictional receipt verified."),
  ).toBeVisible();
  const downloaded = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export draft" }).click();
  const file = await downloaded;
  expect(file.suggestedFilename()).toBe("draft-transactions.csv");
  const content = await readFile((await file.path())!, "utf8");
  expect(content).toContain("Client meeting; fictional receipt verified.");
  expect(content).toContain("needs_review");
  expect(errors).toEqual([]);
});

test("real file input and final export preserve refunds and transfers", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Statement CSV file").setInputFiles({
    name: "final-demo.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "Date,Description,Amount\n2026-04-02,FIGMA,-15\n2026-04-03,REFUND FIGMA,5\n2026-04-04,TRANSFER TO SAVINGS,-100\n",
    ),
  });
  await page
    .getByRole("button", { name: "Import statement", exact: true })
    .last()
    .click();
  await expect(page.getByText("$10.00", { exact: true }).first()).toBeVisible();
  const downloaded = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export final" }).click();
  const file = await downloaded;
  expect(file.suggestedFilename()).toBe("final-transactions.csv");
  expect(await readFile((await file.path())!, "utf8")).toContain(
    "Software,refund,auto",
  );
});

test("invalid rows fail visibly without a partial import", async ({
  page,
  request,
}) => {
  await page.goto("/");
  await page
    .getByLabel("Statement CSV file")
    .setInputFiles(resolve("../samples/invalid-rows.csv"));
  await page
    .getByRole("button", { name: "Import statement", exact: true })
    .last()
    .click();
  await expect(page.getByRole("alert")).toContainText("Nothing was imported");
  await expect(page.getByRole("alert")).toContainText("Row 2:");
  expect(await (await request.get("/api/statements")).json()).toEqual([]);
});

test("duplicate file reuse and keyboard dismissal", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Try a sample statement" }).click();
  await page.getByRole("button", { name: /Review JOES CAFE/ }).click();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page
    .getByRole("button", { name: "Import statement", exact: true })
    .click();
  await page.getByRole("button", { name: "Try a sample statement" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "already imported" }),
  ).toBeVisible();
  await expect(page.getByText("$182.48", { exact: true })).toBeVisible();
});

test("mobile layout contains the table without page overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Try a sample statement" }).click();
  await expect(page.getByText("$182.48", { exact: true })).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Review queue" }).click();
  await expect(
    page.getByRole("button", { name: /Review JOES CAFE/ }),
  ).toBeVisible();
});
