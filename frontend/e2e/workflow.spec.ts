import { test, expect } from "@playwright/test";

test.beforeEach(async ({ request }) => {
  const entries = await (await request.get("/api/statements")).json();
  for (const entry of entries)
    await request.delete(`/api/statements/${entry.statement.id}`);
});

test("actual import, explanation, correction, duplicate review, export and reload", async ({
  page,
  request,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page
    .getByRole("button", { name: "Import your first statement" })
    .click();
  await page
    .getByRole("button", { name: "Explore the synthetic example" })
    .click();
  await expect(
    page.getByText("28 transactions", { exact: false }).first(),
  ).toBeVisible();
  await page.getByLabel("I checked the columns").check();
  await page.getByRole("button", { name: "Import & categorize" }).click();
  await expect(
    page.getByRole("heading", { name: "Statement overview" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "JOES CAFE 9921", exact: true })
    .click();
  await expect(
    page.getByText("Merchant or business purpose is unknown."),
  ).toBeVisible();
  await page.getByLabel("Category", { exact: true }).selectOption("meals");
  await page.getByRole("button", { name: "Save classification" }).click();
  await expect(
    page.getByText("You confirmed this classification."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close transaction details" }).click();
  await page.reload();
  await page
    .getByRole("button", { name: "JOES CAFE 9921", exact: true })
    .click();
  await expect(
    page.getByText("You confirmed this classification."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Reset to engine decision" }).click();
  await expect(
    page.getByText("Merchant or business purpose is unknown."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close transaction details" }).click();
  const duplicateRows = page
    .locator("tr")
    .filter({ hasText: "Possible duplicate" });
  await duplicateRows
    .first()
    .getByRole("button", { name: "FIGMA PROFESSIONAL" })
    .click();
  await page.getByRole("button", { name: "Keep this transaction" }).click();
  await expect(page.getByText("Confirmed separate transaction")).toBeVisible();
  await page.getByRole("button", { name: "Close transaction details" }).click();
  await duplicateRows
    .first()
    .getByRole("button", { name: "FIGMA PROFESSIONAL" })
    .click();
  await page
    .getByRole("button", { name: "Exclude duplicate", exact: true })
    .click();
  await expect(
    page.getByText("Excluded duplicate", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close transaction details" }).click();
  const download = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Export transactions", exact: true })
    .click();
  expect((await download).suggestedFilename()).toBe(
    "ledgerlens-transactions.csv",
  );
  const entries = await (await request.get("/api/statements")).json();
  const report = await (
    await request.get(`/api/statements/${entries[0].statement.id}/summary`)
  ).json();
  expect(report.reconciled).toBe(true);
  expect(report.counts.excluded).toBe(1);
  expect(errors).toEqual([]);
});

test("invalid CSV import is actionable and atomic", async ({
  page,
  request,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Import your first statement" })
    .click();
  await page.getByLabel("Choose CSV file").setInputFiles({
    name: "invalid.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "Date,Description,Amount\n2026-10-01,FIGMA,-10\n2026-02-30,WRONG,-20",
    ),
  });
  await page.getByLabel("I checked the columns").check();
  await page.getByRole("button", { name: "Import & categorize" }).click();
  await expect(page.getByRole("alert")).toContainText("Row 3");
  await expect(page.getByRole("alert")).toContainText("Nothing was imported");
  expect(await (await request.get("/api/statements")).json()).toEqual([]);
});

test("mobile workflow fits screen and permits reviewing and export", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page
    .getByRole("button", { name: "Import your first statement" })
    .click();
  await page
    .getByRole("button", { name: "Explore the synthetic example" })
    .click();
  await page.getByLabel("I checked the columns").check();
  await page.getByRole("button", { name: "Import & categorize" }).click();
  await expect(
    page.getByRole("heading", { name: "Statement overview" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Start reviewing" }).click();
  await expect(
    page.getByRole("complementary", { name: "Transaction review" }),
  ).toBeVisible();
  await page.getByLabel("Category", { exact: true }).selectOption("travel");
  await page.getByRole("button", { name: "Save classification" }).click();
  await expect(
    page.getByText("You confirmed this classification."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close transaction details" }).click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("small statement can be completely reviewed and exported as final", async ({
  page,
  request,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Import your first statement" })
    .click();
  await page.getByLabel("Choose CSV file").setInputFiles({
    name: "small.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "Date,Description,Amount\n2026-10-01,FIGMA,-10\n2026-10-02,UNSEEN COFFEE,-5\n2026-10-03,UNKNOWN CREDIT,30\n2026-10-04,FIGMA REFUND,2",
    ),
  });
  await page.getByLabel("I checked the columns").check();
  await page.getByRole("button", { name: "Import & categorize" }).click();
  await page
    .getByRole("button", { name: "UNSEEN COFFEE", exact: true })
    .click();
  await page
    .getByRole("combobox", { name: "Category", exact: true })
    .selectOption("meals");
  await page.getByRole("button", { name: "Save classification" }).click();
  await expect(
    page.getByText("You confirmed this classification."),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Next transaction needing review" })
    .click();
  await expect(
    page.getByRole("button", { name: "Save classification" }),
  ).toBeDisabled();
  await page
    .getByRole("combobox", { name: "Transaction kind", exact: true })
    .selectOption("income");
  await page.getByRole("button", { name: "Save classification" }).click();
  await expect(
    page.getByRole("heading", { name: "Every transaction accounted for." }),
  ).toBeVisible();
  await expect(page.getByTestId("net-expenses")).toHaveText("$13.00");
  const entry = (await (await request.get("/api/statements")).json())[0];
  expect(
    (
      await request.get(
        `/api/statements/${entry.statement.id}/export?reviewed_only=true`,
      )
    ).status(),
  ).toBe(200);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Every transaction accounted for." }),
  ).toBeVisible();
});

test("last unresolved transaction never reports review completion prematurely", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Import your first statement" })
    .click();
  await page.getByLabel("Choose CSV file").setInputFiles({
    name: "one.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("Date,Description,Amount\n2026-10-01,UNKNOWN,-10"),
  });
  await page.getByLabel("I checked the columns").check();
  await page.getByRole("button", { name: "Import & categorize" }).click();
  await page.getByRole("button", { name: "Start reviewing" }).click();
  await page
    .getByRole("button", { name: "Next transaction needing review" })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "This is the last review item",
  );
  await expect(
    page.getByRole("complementary", { name: "Transaction review" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Every transaction accounted for." }),
  ).toHaveCount(0);
});

test("mobile stale edit error is visible in the panel and reload preserves the newer decision", async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const response = await request.post("/api/statements", {
    multipart: {
      file: {
        name: "conflict.csv",
        mimeType: "text/csv",
        buffer: Buffer.from("Date,Description,Amount\n2026-10-01,UNKNOWN,-10"),
      },
      options: JSON.stringify({
        date_column: "Date",
        description_column: "Description",
        amount_column: "Amount",
        mode: "signed",
        date_format: "iso",
        sign_convention: "negative_outgoing",
        currency: "USD",
      }),
    },
  });
  const sid = (await response.json()).statement.id;
  await page.goto("/");
  await page.getByRole("button", { name: "Start reviewing" }).click();
  const row = (
    await (await request.get(`/api/statements/${sid}/transactions`)).json()
  ).items[0];
  await request.patch(`/api/transactions/${row.id}/review`, {
    data: {
      version: row.version,
      action: "save",
      kind: "expense",
      category: "office",
    },
  });
  await page
    .getByRole("combobox", { name: "Category", exact: true })
    .selectOption("meals");
  await page.getByRole("button", { name: "Save classification" }).click();
  const panel = page.getByRole("complementary", { name: "Transaction review" });
  await expect(panel.getByRole("alert")).toContainText(
    "This transaction changed",
  );
  await expect(panel.getByRole("alert")).toBeInViewport();
  await panel
    .getByRole("button", { name: "Reload transaction and totals" })
    .click();
  await expect(
    panel.getByRole("combobox", { name: "Category", exact: true }),
  ).toHaveValue("office");
  await expect(panel.getByRole("alert")).toHaveCount(0);
});

test("delete dialog contains keyboard focus, Escape cancels and returns focus to its trigger", async ({
  page,
  request,
}) => {
  await request.post("/api/statements", {
    multipart: {
      file: {
        name: "keyboard.csv",
        mimeType: "text/csv",
        buffer: Buffer.from("Date,Description,Amount\n2026-10-01,FIGMA,-10"),
      },
      options: JSON.stringify({
        date_column: "Date",
        description_column: "Description",
        amount_column: "Amount",
        mode: "signed",
        date_format: "iso",
        sign_convention: "negative_outgoing",
        currency: "USD",
      }),
    },
  });
  await page.goto("/");
  const trigger = page.getByRole("button", {
    name: "Delete statement",
    exact: true,
  });
  await trigger.click();
  const dialog = page.getByRole("dialog", { name: "Delete this statement?" });
  await expect(
    dialog.getByRole("button", { name: "Keep statement" }),
  ).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(
    dialog.getByRole("button", { name: "Delete statement", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(
    dialog.getByRole("button", { name: "Keep statement" }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(trigger).toBeFocused();
  expect((await (await request.get("/api/statements")).json()).length).toBe(1);
});
