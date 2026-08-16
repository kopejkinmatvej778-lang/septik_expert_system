import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: {
        accept: "text/html",
        "oai-authenticated-user-id": "test-user",
        "oai-authenticated-user-email": "owner@example.com",
      },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the Septik Expert control panel shell", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>Septik Expert Control<\/title>/i);
  assert.match(html, /Septik Expert/);
  assert.match(html, /Замеры/);
  assert.match(html, /База/);
  assert.match(html, /Монтажи/);
  assert.match(html, /Продажи/);
  assert.match(html, /signin-with-chatgpt|Рабочий центр/);
  assert.doesNotMatch(html, /Your site is taking shape|Building your site|codex-preview/i);
  assert.doesNotMatch(html, /AI Control|AI-питомцы|3D-диспетчерская/i);
});

test("dashboard API no longer creates demo clients or seed documents", async () => {
  const route = await readFile(new URL("../app/api/dashboard/route.ts", import.meta.url), "utf8");
  assert.doesNotMatch(route, /const seedClients|const seedDocuments|const seedMeasurements|const seedMontages|const seedEvents/);
  assert.doesNotMatch(route, /INSERT INTO clients \(name, phone, address, manager, folder_url/);
  assert.doesNotMatch(route, /INSERT INTO montages \(client_id, install_date, status, equipment/);
  assert.match(route, /demoCleanupStatements/);
  assert.match(route, /sales_deals/);
  assert.match(route, /sales_pipelines/);
  assert.match(route, /sales_tasks/);
  assert.match(route, /buildAmoMeasurementRows/);
  assert.match(route, /ответственный\\s\+за\\s\+замер|замерщик/);
});

test("3D scene source is removed from the panel", async () => {
  await assert.rejects(access(new URL("../app/AgentScene.tsx", import.meta.url)));
  const packageJson = await readFile(new URL("../package.json", import.meta.url), "utf8");
  assert.doesNotMatch(packageJson, /"three"|"@types\/three"/);
});

test("client proposals render as PNG photos instead of link-only rows", async () => {
  const dashboard = await readFile(new URL("../app/DashboardClient.tsx", import.meta.url), "utf8");
  assert.match(dashboard, /className="proposal-photo-grid"/);
  assert.match(dashboard, /<Image src=\{document\.fileUrl\}/);
});
