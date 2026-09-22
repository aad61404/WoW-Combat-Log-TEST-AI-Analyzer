import { expect, test, type Page } from "@playwright/test";

async function expectFitsViewport(page: Page) {
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
}

async function openDemo(page: Page) {
  await page.getByRole("button", { name: "開啟範例戰報" }).click();
  await expect(
    page.getByRole("heading", { name: "Nerub-ar Palace · 範例戰報" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "分析戰鬥" }).click();
  await expect(
    page.getByRole("heading", { name: "戰鬥紀錄摘要" }),
  ).toBeVisible();
}

test.beforeEach(async ({ page }) => {
  // Fail closed: browsers in this suite may only reach the isolated local services.
  await page.route("**/*", (route) => {
    const url = new URL(route.request().url());
    return ["http://127.0.0.1:3100", "http://127.0.0.1:8100"].includes(
      url.origin,
    )
      ? route.continue()
      : route.abort();
  });
  await page.goto("/");
});

test("demo completes through real backend with filters, damage details and navigation", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await expect(page.getByLabel("服務設定狀態")).toContainText("未設定");
  await expectFitsViewport(page);
  await openDemo(page);
  await expect(page.locator(".stats")).toContainText("06:32");
  await expect(page.locator(".stats")).toContainText("4 次");
  await expect(page.locator(".timeline .event")).toHaveCount(8);
  await expectFitsViewport(page);
  await page.getByRole("button", { name: "玩家死亡", exact: true }).click();
  await expect(page.locator(".timeline .event")).toHaveCount(4);
  const death = page
    .locator(".timeline .event")
    .filter({ hasText: "ArmsWarr" });
  await death.locator("summary").click();
  await expect(death.locator(".damage-list")).toContainText("120,000");
  await expect(death.locator(".damage-list")).toContainText("55,000");
  await page.getByRole("button", { name: "機制事件", exact: true }).click();
  await expect(page.locator(".timeline .event")).toHaveCount(4);
  await expect(page.locator(".timeline")).toContainText("FrostMage");
  await page.getByRole("button", { name: "返回戰鬥列表" }).click();
  await expect(page.getByRole("button", { name: "分析戰鬥" })).toBeVisible();
  await page.getByRole("button", { name: "更換戰報" }).click();
  await expect(page.getByLabel("WARCRAFT LOGS 網址")).toBeVisible();
  expect(errors).toEqual([]);
});

test("invalid URL is rejected locally and missing credentials produce a useful error", async ({
  page,
}) => {
  let reportRequests = 0;
  page.on("request", (request) => {
    if (request.url().includes("/api/reports/")) reportRequests++;
  });
  await page
    .getByLabel("WARCRAFT LOGS 網址")
    .fill("https://example.com/reports/AbCdEfGh12345678");
  await page.getByRole("button", { name: "讀取戰報" }).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "有效的 Warcraft Logs",
  );
  expect(reportRequests).toBe(0);
  await page.getByLabel("WARCRAFT LOGS 網址").fill("AbCdEfGh12345678");
  await page.getByRole("button", { name: "讀取戰報" }).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "WCL_CLIENT_ID",
  );
  await expectFitsViewport(page);
  await openDemo(page);
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
});

test("failed analysis can be retried without losing the selected report", async ({
  page,
}) => {
  await page.getByRole("button", { name: "開啟範例戰報" }).click();
  await page.route("**/api/demo/fights/1/analysis", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "測試：分析服務暫時不可用" }),
      headers: { "access-control-allow-origin": "http://127.0.0.1:3100" },
    }),
  );
  await page.getByRole("button", { name: "分析戰鬥" }).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "暫時不可用",
  );
  await expect(page.getByRole("button", { name: "分析戰鬥" })).toBeEnabled();
  await page.unroute("**/api/demo/fights/1/analysis");
  await page.getByRole("button", { name: "分析戰鬥" }).click();
  await expect(
    page.getByRole("heading", { name: "戰鬥紀錄摘要" }),
  ).toBeVisible();
});

test("backend unavailable state recovers on explicit refresh", async ({
  page,
}) => {
  await page.route("**/api/status", (route) => route.abort());
  await page.reload();
  await expect(page.getByLabel("服務設定狀態")).toContainText(
    "無法取得後端狀態",
  );
  await page.unroute("**/api/status");
  await page.getByRole("button", { name: "重新檢查" }).click();
  await expect(page.getByLabel("服務設定狀態")).toContainText("WCL · 未設定");
});
