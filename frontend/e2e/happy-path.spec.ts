import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import path from "node:path";

const SAMPLE = path.resolve(__dirname, "../../samples/checking_q1_2026.csv");

async function axe(page: Page) {
  const r = await new AxeBuilder({ page }).analyze();
  const bad = r.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(bad, JSON.stringify(bad.map((v) => v.id))).toEqual([]);
}

test("upload, review, summary, export", async ({ page }) => {
  await page.goto("/");
  await axe(page);
  await page.getByLabel("Checking").check();
  await page.getByLabel(/Drop a CSV or OFX file/).setInputFiles(SAMPLE);

  await expect(page).toHaveURL(/\/statements\/[^/]+$/);
  const reviewTab = page.getByRole("tab", { name: /Needs your review/ });
  await expect(reviewTab).toBeVisible();
  const before = Number((await reviewTab.innerText()).match(/(\d+)\s*$/)?.[1]);
  expect(before).toBeGreaterThan(0);
  await axe(page);

  await page.getByPlaceholder("Search").fill("JOES CAFE");
  await page.getByRole("button", { name: /JOES CAFE/i }).first().click();
  await page.getByRole("button", { name: /^\d?\s*Personal/ }).first().click();
  await page.getByLabel(/Remember for/).check();
  await page.getByRole("button", { name: "Confirm" }).click();
  await page.getByPlaceholder("Search").fill("");
  await expect(reviewTab).not.toContainText(String(before));

  await page.getByRole("link", { name: "Schedule E summary" }).click();
  await expect(page.getByRole("heading", { name: /Schedule E, Part I/ })).toBeVisible();
  await expect(page.getByRole("rowheader", { name: "3" })).toBeVisible();
  await axe(page);

  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Export CSV" }).click();
  const file = await download;
  const stream = await file.createReadStream();
  let text = "";
  for await (const chunk of stream) text += chunk.toString();
  expect(text.split("\n")[0]).toContain("date,description,amount,category");
});
