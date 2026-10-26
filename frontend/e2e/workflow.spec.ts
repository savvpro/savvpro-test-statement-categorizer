import { expect, test } from "@playwright/test";
import { resolve } from "node:path";
const samples = resolve(import.meta.dirname, "../../sample_data");

test.beforeEach(async ({ request }) => {
  const data = await (await request.get("/api/workspace")).json();
  for (const s of data.statements)
    await request.delete(`/api/statements/${s.id}`);
  for (const r of data.rules) await request.delete(`/api/rules/${r.id}`);
});

test("upload, explain, review a mixed expense, persist, report and export", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await page.goto("/");
  await expect(page).toHaveTitle(/SortedHisab/);
  await page
    .getByRole("button", { name: "Upload your first statement" })
    .click();
  await page
    .getByLabel("Statement file")
    .setInputFiles(resolve(samples, "developer-credit-card.csv"));
  await page.getByLabel("Account name").fill("Demo developer card");
  await page.getByRole("button", { name: "Validate & preview" }).click();
  await expect(page.getByText("36 of 36 rows valid")).toBeVisible();
  await page.getByRole("button", { name: "Import 36 transactions" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByLabel("Search transactions").fill("NAYATEL");
  await page.getByRole("button", { name: "Review NAYATEL INTERNET" }).click();
  await page.getByLabel("Search transactions").fill("");
  const review = page.getByRole("complementary", {
    name: "Review transaction",
  });
  await expect(
    review.getByText("Business purpose cannot be determined", { exact: false }),
  ).toBeVisible();
  await review.getByLabel("Purpose", { exact: true }).selectOption("mixed");
  await review.getByLabel("Business share").fill("60");
  await review.getByLabel("Notes").fill("Home internet: 60% professional use.");
  await review.getByRole("checkbox").check();
  await review.getByRole("button", { name: "Save review" }).click();
  await expect(page.getByText("Review saved. Totals updated.")).toBeVisible();
  await expect(page.locator(".business-metric strong")).toContainText("2,520");
  await page.reload();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Rules" })
    .click();
  await expect(
    page.getByText("NAYATEL INTERNET", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Overview" })
    .click();
  await expect(page.getByText("Every row accounted for")).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "Export CSV", exact: true }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("sortedhisab-transactions.csv");
  await page
    .getByRole("navigation")
    .getByRole("button", { name: /Transactions/ })
    .click();
  await page.getByLabel("Search transactions").fill("NAYATEL");
  await page.getByRole("button", { name: "Review NAYATEL INTERNET" }).click();
  await page.getByLabel("Search transactions").fill("");
  await page.screenshot({
    path: process.env.QA_DIR
      ? resolve(process.env.QA_DIR, "desktop-review.png")
      : test.info().outputPath("desktop-review.png"),
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("invalid source rows remain visible and cannot be imported", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Upload your first statement" })
    .click();
  await page
    .getByLabel("Statement file")
    .setInputFiles(resolve(samples, "invalid-rows.csv"));
  await page.getByLabel("Account name").fill("Invalid demo");
  await page.getByRole("button", { name: "Validate & preview" }).click();
  await expect(page.getByText("1 of 5 rows valid")).toBeVisible();
  await expect(page.getByText(/Row 3: Invalid date/)).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Import \d+ transactions/ }),
  ).toHaveCount(0);
});

test("mobile demo, search and review fit without page overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Explore a demo" }).click();
  await expect(page.getByLabel("Search transactions")).toBeVisible();
  await page.getByLabel("Search transactions").fill("NETFLIX");
  await expect(
    page.getByRole("button", { name: "Review NETFLIX MONTHLY" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await expect(page.locator(".toast")).toHaveCount(0);
  await page.screenshot({
    path: process.env.QA_DIR
      ? resolve(process.env.QA_DIR, "mobile.png")
      : test.info().outputPath("mobile.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Review NETFLIX MONTHLY" }).click();
  await expect(page.getByRole("button", { name: "Save review" })).toBeVisible();
  await page.getByRole("button", { name: "Close review" }).click();
  await expect(
    page.getByRole("complementary", { name: "Review transaction" }),
  ).toHaveCount(0);
});

test("PDF and XLSX import through the same review workflow", async ({
  page,
}) => {
  await page.goto("/");
  for (const extension of ["pdf", "xlsx"]) {
    await page
      .getByRole("button", { name: "Upload statement", exact: true })
      .click();
    await page
      .getByLabel("Statement file")
      .setInputFiles(resolve(samples, `developer-statement.${extension}`));
    await page.getByLabel("Account name").fill(`Demo ${extension}`);
    await page.getByRole("button", { name: "Validate & preview" }).click();
    await expect(page.getByText("12 of 12 rows valid")).toBeVisible();
    await page.getByRole("button", { name: "Import 12 transactions" }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
  }
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Statements" })
    .click();
  await expect(
    page.getByRole("heading", { name: "developer-statement.pdf" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "developer-statement.xlsx" }),
  ).toBeVisible();
});
