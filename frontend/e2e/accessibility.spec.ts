import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("welcome, import and review workspace have no automated WCAG AA violations", async ({
  page,
  request,
}) => {
  for (const entry of await (await request.get("/api/statements")).json())
    await request.delete(`/api/statements/${entry.statement.id}`);
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Import your first statement" }),
  ).toBeVisible();
  for (const stage of ["welcome", "upload", "mapping", "workspace", "review"]) {
    if (stage === "upload")
      await page
        .getByRole("button", { name: "Import your first statement" })
        .click();
    if (stage === "mapping")
      await page
        .getByRole("button", { name: "Explore the synthetic example" })
        .click();
    if (stage === "workspace") {
      await page.getByLabel("I checked the columns").check();
      await page.getByRole("button", { name: "Import & categorize" }).click();
      await expect(
        page.getByRole("heading", { name: "Statement overview" }),
      ).toBeVisible();
    }
    if (stage === "review")
      await page
        .getByRole("button", { name: "JOES CAFE 9921", exact: true })
        .click();
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(
      results.violations.map((v) => ({
        id: v.id,
        nodes: v.nodes.map((n) => ({
          html: n.html,
          summary: n.failureSummary,
        })),
      })),
      stage,
    ).toEqual([]);
  }
});
