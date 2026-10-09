import { expect, test } from "@playwright/test";

test("add, schema edit, drag, resize and undo an element", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#status")).toContainText("Rendered");
  await expect(page.locator("#version")).toHaveText(/^v\d+\.\d+\.\d+$/);
  const metadata = await page.evaluate(async () =>
    (
      await fetch("/api/metadata", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: "{}",
      })
    ).json(),
  );
  expect(metadata.designer_version).toBe(
    (await page.locator("#version").textContent()).slice(1),
  );
  expect(metadata.imagespec_minimum_version).toBe("1.0.1");
  expect(metadata.imagespec_tested_version).toBe("1.0.1");
  await expect(page.locator(".type-button")).toHaveCount(30);
  await page.getByRole("button", { name: "rectangle +" }).click();
  const frame = page.locator(".frame.selected");
  await expect(frame).toBeVisible();
  await expect(page.locator('[data-key="x_start"]')).toHaveCount(0);
  const fill = page.locator('[data-key="fill"]');
  await fill.fill("red");
  await fill.press("Tab");
  await expect(page.locator("#status")).toContainText("Rendered");
  const start = await frame.boundingBox();
  await page.mouse.move(start.x + 20, start.y + 20);
  await page.mouse.down();
  await page.mouse.move(start.x + 35, start.y + 29);
  await page.mouse.up();
  const moved = await frame.boundingBox();
  expect(Math.round((moved.x - start.x) / 3)).toBe(5);
  const resize = page.locator(".frame.selected .resize");
  const resizeBox = await resize.boundingBox();
  await page.mouse.move(resizeBox.x + 4, resizeBox.y + 4);
  await page.mouse.down();
  await page.mouse.move(resizeBox.x + 16, resizeBox.y + 13);
  await page.mouse.up();
  const apiState = await page.evaluate(() =>
    window.imagespecDesigner?.getDocument(),
  );
  expect(apiState.elements[0].width).toBeGreaterThan(80);
  await page.keyboard.press("Control+z");
  await expect
    .poll(
      async () =>
        (await page.evaluate(() => window.imagespecDesigner.getDocument()))
          .elements[0].width,
    )
    .toBe(80);
});

test("import imagespec YAML, export payload and apply a template", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Import YAML" }).click();
  await page
    .locator("#yaml")
    .fill(
      "- type: rectangle\n  x_start: 2\n  y_start: 3\n  x_end: 24\n  y_end: 18\n  fill: black\n",
    );
  await page.locator("#dialog-apply").click();
  await expect(page.locator("#yaml-dialog")).not.toBeVisible();
  expect(
    await page.evaluate(() => window.imagespecDesigner.getDocument().elements),
  ).toHaveLength(1);
  await page.getByRole("button", { name: "Export imagespec YAML" }).click();
  await expect(page.locator("#yaml")).toHaveValue(/x_start: 2/);
  await page.locator("#yaml-dialog button[value=cancel]").click();
  await page.getByRole("button", { name: "Templates" }).click();
  await page.getByRole("button", { name: /Simple card/ }).click();
  await page
    .locator('#template-params input[data-param="title"]')
    .fill("Browser test");
  await page.locator("#template-apply").click();
  await expect(page.locator("#status")).toContainText("Template loaded");
  const doc = await page.evaluate(() => window.imagespecDesigner.getDocument());
  expect(doc.elements).toHaveLength(3);
  expect(doc.elements[1].spec.value).toBe("Browser test");
});

test("partial YAML imports keep their skipped-item explanation visible", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Import YAML" }).click();
  await page
    .locator("#yaml")
    .fill(
      "- type: text\n  x: 4\n  y: 5\n  value: kept\n- type: text\n  x: 8\n  value: skipped\n",
    );
  await page.locator("#dialog-apply").click();
  await expect(page.locator("#status")).toContainText("#2 text");
  expect(
    await page.evaluate(() => window.imagespecDesigner.getDocument().elements),
  ).toHaveLength(1);
});

test("selecting a layer updates the canvas frame outline", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Import YAML" }).click();
  await page
    .locator("#yaml")
    .fill(
      "- type: rectangle\n  x_start: 2\n  y_start: 3\n  x_end: 24\n  y_end: 18\n  fill: black\n- type: text\n  x: 30\n  y: 10\n  value: Layer\n",
    );
  await page.locator("#dialog-apply").click();
  const layer = page.locator(".layer", { hasText: "text" });
  await layer.click();
  const selection = await page.evaluate(() => {
    const selectedFrame = document.querySelector(".frame.selected");
    const text = window.imagespecDesigner
      .getDocument()
      .elements.find((element) => element.spec.type === "text");
    return {
      frameId: selectedFrame?.dataset.id,
      textId: text?.id,
      resizeHandles: document.querySelectorAll(".frame .resize").length,
    };
  });
  expect(selection).toEqual({
    frameId: selection.textId,
    textId: selection.textId,
    resizeHandles: 1,
  });
});

test("two embedded editor instances keep their documents independent", async ({
  page,
}) => {
  await page.goto("/");
  await page.evaluate(async () => {
    const { mount } = await import("/assets/embed.js");
    const a = document.createElement("div"),
      b = document.createElement("div");
    a.id = "embed-a";
    b.id = "embed-b";
    document.body.append(a, b);
    const host = {
      apiBase: "/api",
      profile: { width: 200, height: 120, palette: "bw", name: "Embedded" },
    };
    window.embeddedA = await mount(a, { ...host, title: "Editor A" });
    window.embeddedB = await mount(b, { ...host, title: "Editor B" });
    await window.embeddedA.setDocument({
      version: 1,
      canvas: { width: 200, height: 120 },
      background: "white",
      elements: [
        {
          id: "a-title",
          type: "imagespec",
          x: 4,
          y: 5,
          width: 90,
          height: 30,
          spec: { type: "text", value: "Only in A", size: 18 },
        },
      ],
    });
  });
  const independent = await page.evaluate(async () => {
    const a = await window.embeddedA.getDocument();
    const b = await window.embeddedB.getDocument();
    await window.embeddedA.refresh();
    const valid = await window.embeddedA.validate(a);
    return [
      a.elements.length,
      b.elements.length,
      window.embeddedA.frame.title,
      window.embeddedB.frame.title,
      valid.valid,
    ];
  });
  expect(independent).toEqual([1, 0, "Editor A", "Editor B", true]);
});
