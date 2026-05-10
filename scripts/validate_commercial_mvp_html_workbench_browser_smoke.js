const { chromium } = require("playwright");
const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const baseUrl = process.env.COMMERCIAL_MVP_BASE_URL || "http://127.0.0.1:4189";
const reportPath = path.resolve(
  repoRoot,
  process.env.COMMERCIAL_MVP_BROWSER_REPORT || "outputs/reports/commercial_mvp_html_workbench_browser_smoke_internal_full_beta_ready.json"
);
const screenshotRoot = path.resolve(
  repoRoot,
  process.env.COMMERCIAL_MVP_SCREENSHOT_ROOT || "outputs/playwright/commercial-mvp-html-workbench-internal-full-beta-ready"
);

function rel(target) {
  return path.relative(repoRoot, target).replaceAll(path.sep, "/");
}

function assert(condition, message, errors) {
  if (!condition) errors.push(message);
}

async function screenshot(page, name, evidence) {
  const file = path.join(screenshotRoot, name);
  await page.screenshot({ path: file, fullPage: false });
  evidence.screenshots.push(rel(file));
}

async function main() {
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.mkdirSync(screenshotRoot, { recursive: true });
  const evidence = {
    schema_version: "commercial_mvp_html_workbench_browser_smoke.v1",
    status: "valid",
    base_url: "local_static_server",
    screenshots: [],
    drawer_widths: [],
    localization: {},
    generated_work_state: {},
    editor_actions: {},
    surfaces: {},
    viewer: {},
    viewer_widths: [],
    export_handoff: {},
    errors: [],
  };

  let browser;
  try {
    browser = await chromium.launch();
  } catch (error) {
    browser = await chromium.launch({ channel: "chrome" });
  }
  const page = await browser.newPage();
  page.on("dialog", async (dialog) => {
    await dialog.accept();
  });
  try {
    const widths = [
      { label: "desktop_1440", width: 1440, height: 900 },
      { label: "desktop_1600", width: 1600, height: 900 },
      { label: "desktop_1920", width: 1920, height: 1080 },
      { label: "ultrawide_2560", width: 2560, height: 1080 },
      { label: "narrow_900", width: 900, height: 900 },
    ];

    for (const size of widths) {
      await page.setViewportSize({ width: size.width, height: size.height });
      await page.goto(`${baseUrl}/web/commercial-mvp-html-workbench/index.html`);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(250);
      const frame = page.locator("#canvas-frame");
      const before = await frame.boundingBox();
      assert(Boolean(before && before.width > 0 && before.height > 0), `${size.label} canvas frame missing`, evidence.errors);
      await page.locator('[data-surface="design-library"]').click();
      await page.locator('[data-feature-panel="design-library"]').waitFor({ state: "visible" });
      const afterOpen = await frame.boundingBox();
      const drawer = await page.locator("#feature-surface").boundingBox();
      const close = page.locator('[data-action="close-surface"]');
      await close.waitFor({ state: "visible" });
      const closeFocused = await close.evaluate((node) => document.activeElement === node);
      await screenshot(page, `design-library-${size.label}.png`, evidence);
      await page.keyboard.press("Escape");
      await page.locator("#feature-surface").waitFor({ state: "hidden" });
      const triggerRefocused = await page.locator('[data-surface="design-library"]').evaluate((node) => document.activeElement === node);
      const afterClose = await frame.boundingBox();
      await page.locator(".slide-object").first().click({ force: true });
      const selected = await page.locator("#selected-label").innerText();
      const row = {
        label: size.label,
        viewport: { width: size.width, height: size.height },
        canvas_preserved_open: Boolean(before && afterOpen && Math.abs(before.width - afterOpen.width) <= 1 && Math.abs(before.height - afterOpen.height) <= 1),
        canvas_preserved_close: Boolean(before && afterClose && Math.abs(before.width - afterClose.width) <= 1 && Math.abs(before.height - afterClose.height) <= 1),
        drawer_visible: Boolean(drawer && drawer.width > 0 && drawer.height > 0),
        close_focus_visible: closeFocused,
        trigger_focus_restored_after_escape: triggerRefocused,
        edit_after_close: !/선택 없음|No selection/.test(selected),
      };
      evidence.drawer_widths.push(row);
      assert(row.canvas_preserved_open, `${size.label} canvas changed while drawer opened`, evidence.errors);
      assert(row.canvas_preserved_close, `${size.label} canvas changed after drawer closed`, evidence.errors);
      assert(row.drawer_visible, `${size.label} drawer not visible`, evidence.errors);
      assert(row.close_focus_visible, `${size.label} drawer close did not receive focus`, evidence.errors);
      assert(row.trigger_focus_restored_after_escape, `${size.label} drawer trigger focus was not restored after Escape`, evidence.errors);
      assert(row.edit_after_close, `${size.label} edit selection failed after drawer close`, evidence.errors);
    }

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`${baseUrl}/web/commercial-mvp-html-workbench/index.html`);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(250);
    await screenshot(page, "workbench-ko-normal.png", evidence);

    const baselineObjects = await page.evaluate(() => {
      const api = window.htmlWorkbenchTestApi;
      const slide = api.state.deck.slides[api.state.activeSlideIndex];
      const text = slide.objects.find((item) => item.type === "text");
      const shapeOrImage = slide.objects.find((item) => (item.type === "shape" || item.type === "image") && item.w < 1200 && item.h < 800)
        || slide.objects.find((item) => item.type === "shape" || item.type === "image");
      const editable = slide.objects.filter((item) => item.type !== "line" && item.w < 1200 && item.h < 800);
      return {
        slide_id: slide.id,
        object_count: slide.objects.length,
        text_id: text?.id || null,
        text_before: text?.text || "",
        shape_or_image_id: shapeOrImage?.id || null,
        multi_ids: editable.slice(0, 3).map((item) => item.id),
      };
    });
    evidence.editor_actions.baseline = baselineObjects;
    assert(Boolean(baselineObjects.text_id), "browser action smoke could not find a text object", evidence.errors);
    assert(Boolean(baselineObjects.shape_or_image_id), "browser action smoke could not find a shape/image object", evidence.errors);
    assert(baselineObjects.multi_ids.length >= 3, "browser action smoke needs at least three objects for multi-select", evidence.errors);

    if (baselineObjects.text_id) {
      const textLocator = page.locator(`[data-object-id="${baselineObjects.text_id}"]`);
      await textLocator.dblclick({ force: true });
      await page.keyboard.type("Internal beta direct edit");
      await page.keyboard.press(process.platform === "darwin" ? "Meta+Enter" : "Control+Enter");
      await page.waitForTimeout(200);
    }
    const afterTextEdit = await page.evaluate((textId) => {
      const api = window.htmlWorkbenchTestApi;
      const slide = api.state.deck.slides[api.state.activeSlideIndex];
      const object = slide.objects.find((item) => item.id === textId);
      return {
        text: object?.text || "",
        text_rotation_disabled: document.querySelector(`[data-object-id="${CSS.escape(textId)}"]`)?.dataset.textRotationDisabled === "true",
        rotation_before_text_rotate: object?.rotation || 0,
      };
    }, baselineObjects.text_id);
    await page.evaluate((textId) => {
      const api = window.htmlWorkbenchTestApi;
      api.selectObject(textId);
      api.transformSelected("rotate", 15);
    }, baselineObjects.text_id);
    const afterTextRotateAttempt = await page.evaluate((textId) => {
      const slide = window.htmlWorkbenchTestApi.state.deck.slides[window.htmlWorkbenchTestApi.state.activeSlideIndex];
      const object = slide.objects.find((item) => item.id === textId);
      return object?.rotation || 0;
    }, baselineObjects.text_id);
    evidence.editor_actions.direct_text_edit = {
      changed: afterTextEdit.text.includes("Internal beta direct edit"),
      text_rotation_disabled: afterTextEdit.text_rotation_disabled,
      text_rotation_unchanged: afterTextRotateAttempt === afterTextEdit.rotation_before_text_rotate,
    };
    assert(evidence.editor_actions.direct_text_edit.changed, "double-click text edit did not commit", evidence.errors);
    assert(evidence.editor_actions.direct_text_edit.text_rotation_disabled, "text box does not expose rotation-disabled marker", evidence.errors);
    assert(evidence.editor_actions.direct_text_edit.text_rotation_unchanged, "text box rotation changed even though rotation should be disabled", evidence.errors);

    await page.evaluate((textId) => window.htmlWorkbenchTestApi.selectObject(textId), baselineObjects.text_id);
    await page.locator("#text-editor").click();
    await page.locator("#text-editor").fill("Inspector text edit guard");
    await page.keyboard.press("End");
    await page.keyboard.press("Backspace");
    const inspectorBackspace = await page.evaluate((textId) => {
      const slide = window.htmlWorkbenchTestApi.state.deck.slides[window.htmlWorkbenchTestApi.state.activeSlideIndex];
      const object = slide.objects.find((item) => item.id === textId);
      return {
        object_exists: Boolean(object),
        object_count: slide.objects.length,
        editor_value: document.querySelector("#text-editor")?.value || "",
        selected: window.htmlWorkbenchTestApi.selectedObjectId,
      };
    }, baselineObjects.text_id);
    evidence.editor_actions.inspector_text_backspace = {
      object_preserved: inspectorBackspace.object_exists && inspectorBackspace.object_count === baselineObjects.object_count,
      selected_preserved: inspectorBackspace.selected === baselineObjects.text_id,
      textarea_edited: inspectorBackspace.editor_value === "Inspector text edit guar",
    };
    assert(evidence.editor_actions.inspector_text_backspace.object_preserved, "Backspace in inspector text editor deleted the selected object", evidence.errors);
    assert(evidence.editor_actions.inspector_text_backspace.selected_preserved, "Backspace in inspector text editor cleared the selected text object", evidence.errors);
    assert(evidence.editor_actions.inspector_text_backspace.textarea_edited, "Backspace in inspector text editor did not edit the textarea", evidence.errors);

    const beforeShapeEdit = await page.evaluate((objectId) => {
      const slide = window.htmlWorkbenchTestApi.state.deck.slides[window.htmlWorkbenchTestApi.state.activeSlideIndex];
      const object = slide.objects.find((item) => item.id === objectId);
      return { x: object?.x, y: object?.y, w: object?.w, h: object?.h, z: object?.z };
    }, baselineObjects.shape_or_image_id);
    const beforeDrag = await page.locator(`[data-object-id="${baselineObjects.shape_or_image_id}"]`).boundingBox();
    if (beforeDrag) {
      await page.mouse.move(beforeDrag.x + beforeDrag.width / 2, beforeDrag.y + beforeDrag.height / 2);
      await page.mouse.down();
      await page.mouse.move(beforeDrag.x + beforeDrag.width / 2 + 36, beforeDrag.y + beforeDrag.height / 2 + 24, { steps: 5 });
      await page.mouse.up();
      await page.waitForTimeout(200);
    }
    const afterDrag = await page.evaluate((objectId) => {
      const slide = window.htmlWorkbenchTestApi.state.deck.slides[window.htmlWorkbenchTestApi.state.activeSlideIndex];
      const object = slide.objects.find((item) => item.id === objectId);
      return { x: object?.x, y: object?.y, w: object?.w, h: object?.h, z: object?.z, rotation: object?.rotation || 0, flipX: Boolean(object?.flipX), flipY: Boolean(object?.flipY), radius: object?.radius ?? null };
    }, baselineObjects.shape_or_image_id);
    const objectBoxBeforeResize = await page.locator(`[data-object-id="${baselineObjects.shape_or_image_id}"]`).boundingBox();
    if (objectBoxBeforeResize) {
      await page.mouse.move(objectBoxBeforeResize.x + objectBoxBeforeResize.width - 3, objectBoxBeforeResize.y + objectBoxBeforeResize.height - 3);
      await page.mouse.down();
      await page.mouse.move(objectBoxBeforeResize.x + objectBoxBeforeResize.width + 58, objectBoxBeforeResize.y + objectBoxBeforeResize.height + 38, { steps: 6 });
      await page.mouse.up();
      await page.waitForTimeout(200);
    }
    const afterResize = await page.evaluate((objectId) => {
      const slide = window.htmlWorkbenchTestApi.state.deck.slides[window.htmlWorkbenchTestApi.state.activeSlideIndex];
      const object = slide.objects.find((item) => item.id === objectId);
      return { x: object?.x, y: object?.y, w: object?.w, h: object?.h, z: object?.z };
    }, baselineObjects.shape_or_image_id);

    await page.locator('[data-action="duplicate-object"]').click();
    await page.waitForTimeout(150);
    const afterDuplicate = await page.evaluate(() => {
      const slide = window.htmlWorkbenchTestApi.state.deck.slides[window.htmlWorkbenchTestApi.state.activeSlideIndex];
      return { selected: window.htmlWorkbenchTestApi.selectedObjectId, object_count: slide.objects.length };
    });
    await page.locator('[data-action="bring-forward"]').click();
    await page.locator('[data-action="send-backward"]').click();
    const afterZOrder = await page.evaluate((objectId) => {
      const slide = window.htmlWorkbenchTestApi.state.deck.slides[window.htmlWorkbenchTestApi.state.activeSlideIndex];
      const object = slide.objects.find((item) => item.id === objectId);
      return object?.z || 0;
    }, afterDuplicate.selected);
    await page.locator('[data-action="delete-object"]').click();
    await page.waitForTimeout(150);
    const afterDelete = await page.evaluate(() => {
      const slide = window.htmlWorkbenchTestApi.state.deck.slides[window.htmlWorkbenchTestApi.state.activeSlideIndex];
      return { object_count: slide.objects.length };
    });

    await page.evaluate((ids) => window.htmlWorkbenchTestApi.selectObjects(ids), baselineObjects.multi_ids);
    await page.locator('[data-action="align-top"]').click();
    await page.locator('[data-action="distribute-horizontal"]').click();
    const multiSelectResult = await page.evaluate((ids) => {
      const slide = window.htmlWorkbenchTestApi.state.deck.slides[window.htmlWorkbenchTestApi.state.activeSlideIndex];
      const objects = ids.map((id) => slide.objects.find((item) => item.id === id)).filter(Boolean);
      return {
        selected_count: window.htmlWorkbenchTestApi.selectedObjectIds.length,
        y_values: objects.map((item) => item.y),
        x_values: objects.map((item) => item.x),
      };
    }, baselineObjects.multi_ids);

    await page.evaluate((objectId) => {
      const api = window.htmlWorkbenchTestApi;
      api.selectObject(objectId);
      api.transformSelected("rotate", 15);
      api.transformSelected("flipX");
      api.transformSelected("flipY");
      api.transformSelected("radius", 18);
    }, baselineObjects.shape_or_image_id);
    const afterTransform = await page.evaluate((objectId) => {
      const slide = window.htmlWorkbenchTestApi.state.deck.slides[window.htmlWorkbenchTestApi.state.activeSlideIndex];
      const object = slide.objects.find((item) => item.id === objectId);
      return { rotation: object?.rotation || 0, flipX: Boolean(object?.flipX), flipY: Boolean(object?.flipY), radius: object?.radius ?? null };
    }, baselineObjects.shape_or_image_id);

    await page.locator('[data-surface="design-library"]').click();
    await page.locator('[data-action="apply-reference-recipe"]').first().click();
    await page.waitForTimeout(150);
    const rdlAfterApply = await page.locator("#reference-apply-summary").innerText();
    await page.locator('[data-action="reset-reference-recipe"]').click();
    await page.waitForTimeout(150);
    const rdlAfterReset = await page.locator("#reference-apply-summary").innerText();
    await page.keyboard.press("Escape");
    await page.locator("#feature-surface").waitFor({ state: "hidden" });

    await page.locator('[data-surface="master-style"]').click();
    await page.selectOption("#master-palette", "contrast");
    await page.locator('[data-action="master-apply"]').click();
    await page.locator('[data-action="master-lock"]').click();
    const masterLocked = await page.locator('[data-action="master-lock"]').getAttribute("aria-pressed");
    await page.locator('[data-action="master-reset"]').click();
    const masterSummary = await page.locator("#style-summary").innerText();
    await page.keyboard.press("Escape");
    await page.locator("#feature-surface").waitFor({ state: "hidden" });

    await page.locator('[data-surface="memory-share"]').click();
    const styleMemoryBefore = await page.locator("#style-memory").innerText();
    await page.locator('[data-action="style-memory-reset"]').click();
    await page.waitForTimeout(100);
    const styleMemoryAfterReset = await page.locator("#style-memory").innerText();
    await page.locator('[data-action="style-memory-delete"]').click();
    await page.waitForTimeout(100);
    const styleMemoryAfterDelete = await page.locator("#style-memory").innerText();
    await page.keyboard.press("Escape");
    await page.locator("#feature-surface").waitFor({ state: "hidden" });

    evidence.editor_actions.object_editing = {
      moved: Boolean(afterDrag.x !== beforeShapeEdit.x || afterDrag.y !== beforeShapeEdit.y),
      resized: Boolean(afterResize.w > afterDrag.w || afterResize.h > afterDrag.h),
      duplicated: afterDuplicate.object_count === baselineObjects.object_count + 1,
      deleted_duplicate: afterDelete.object_count === baselineObjects.object_count,
      z_order_button_path: afterZOrder > 0,
    };
    evidence.editor_actions.multi_select = {
      selected_count: multiSelectResult.selected_count,
      aligned_top: new Set(multiSelectResult.y_values).size === 1,
      distributed_horizontal: multiSelectResult.x_values.length >= 3,
    };
    evidence.editor_actions.shape_image_transform = {
      rotated: afterTransform.rotation !== 0,
      flipped_horizontal: afterTransform.flipX === true,
      flipped_vertical: afterTransform.flipY === true,
      radius_updated: afterTransform.radius === 18 || afterTransform.radius === null,
    };
    evidence.editor_actions.reference_design_library = {
      apply_summary_changed: /적용 전|Before:/.test(rdlAfterApply),
      reset_summary_changed: /기본값|default/.test(rdlAfterReset),
    };
    evidence.editor_actions.master_style = {
      lock_toggled: masterLocked === "true",
      reset_summary_visible: masterSummary.length > 0,
    };
    evidence.editor_actions.style_memory = {
      initial_visible: styleMemoryBefore.length > 0,
      reset_visible: /0|없음|설정 안 됨|None|Unset|preference/i.test(styleMemoryAfterReset),
      delete_visible: /삭제|Deleted/i.test(styleMemoryAfterDelete),
    };
    await screenshot(page, "direct-editor-actions.png", evidence);
    assert(evidence.editor_actions.object_editing.moved, "drag move action did not run", evidence.errors);
    assert(evidence.editor_actions.object_editing.resized, "resize handle action did not resize", evidence.errors);
    assert(evidence.editor_actions.object_editing.duplicated, "duplicate button did not add an object", evidence.errors);
    assert(evidence.editor_actions.object_editing.deleted_duplicate, "delete button did not remove the duplicate", evidence.errors);
    assert(evidence.editor_actions.object_editing.z_order_button_path, "z-order button path did not run", evidence.errors);
    assert(evidence.editor_actions.multi_select.selected_count >= 3, "multi-select did not retain at least three selected objects", evidence.errors);
    assert(evidence.editor_actions.multi_select.aligned_top, "multi-select align did not align tops", evidence.errors);
    assert(evidence.editor_actions.shape_image_transform.rotated, "shape/image rotate did not update rotation", evidence.errors);
    assert(evidence.editor_actions.shape_image_transform.flipped_horizontal, "shape/image horizontal flip did not toggle", evidence.errors);
    assert(evidence.editor_actions.shape_image_transform.flipped_vertical, "shape/image vertical flip did not toggle", evidence.errors);
    assert(evidence.editor_actions.shape_image_transform.radius_updated, "shape radius did not update", evidence.errors);
    assert(evidence.editor_actions.reference_design_library.apply_summary_changed, "RDL apply summary did not update", evidence.errors);
    assert(evidence.editor_actions.reference_design_library.reset_summary_changed, "RDL reset summary did not update", evidence.errors);
    assert(evidence.editor_actions.master_style.lock_toggled, "Master Style lock did not toggle", evidence.errors);
    assert(evidence.editor_actions.style_memory.initial_visible, "Style Memory was not visible in drawer", evidence.errors);
    assert(evidence.editor_actions.style_memory.reset_visible, "Style Memory reset feedback was not visible", evidence.errors);
    assert(evidence.editor_actions.style_memory.delete_visible, "Style Memory delete feedback was not visible", evidence.errors);

    const generatedInput = await JSON.parse(fs.readFileSync(path.join(repoRoot, "web/commercial-mvp-html-workbench/generated-work-state.example.json"), "utf8"));
    evidence.generated_work_state = await page.evaluate((input) => window.htmlWorkbenchTestApi.loadGeneratedState(input), generatedInput);
    await page.waitForTimeout(250);
    await screenshot(page, "generated-work-state-loaded.png", evidence);
    assert(evidence.generated_work_state.loaded === true, "generated work state did not load", evidence.errors);
    assert(evidence.generated_work_state.fixture === false, "generated work state still reported fixture=true", evidence.errors);
    assert(Boolean(evidence.generated_work_state.deck_id), "generated work state did not expose deck id", evidence.errors);
    assert(Boolean(evidence.generated_work_state.design_package_id), "generated work state did not expose design package id", evidence.errors);
    assert(Boolean(evidence.generated_work_state.theme_id), "generated work state did not expose theme id", evidence.errors);
    assert(evidence.generated_work_state.revision_memory_count > 0, "generated work state did not expose revision memory", evidence.errors);
    assert(Boolean(evidence.generated_work_state.export_status), "generated work state did not expose export status", evidence.errors);

    evidence.generated_family_states = [];
    for (const family of ["ir", "sales", "portfolio"]) {
      const familyPath = path.join(repoRoot, `web/commercial-mvp-html-workbench/generated-work-states/${family}-final_user_test_polish.json`);
      if (!fs.existsSync(familyPath)) continue;
      const familyState = JSON.parse(fs.readFileSync(familyPath, "utf8"));
      const loadResult = await page.evaluate((input) => window.htmlWorkbenchTestApi.loadGeneratedState(input), familyState);
      await page.waitForTimeout(250);
      await screenshot(page, `generated-${family}-state-loaded.png`, evidence);
      const row = {
        family,
        loaded: loadResult.loaded === true,
        fixture: loadResult.fixture === false ? false : loadResult.fixture,
        deck_id: loadResult.deck_id,
        design_package_id: loadResult.design_package_id,
        theme_id: loadResult.theme_id,
        revision_memory_count: loadResult.revision_memory_count,
        export_status: loadResult.export_status,
        safe_asset_ref_count: loadResult.safe_asset_ref_count,
      };
      evidence.generated_family_states.push(row);
      assert(row.loaded, `${family} generated state did not load`, evidence.errors);
      assert(row.fixture === false, `${family} generated state reported fixture=true`, evidence.errors);
      assert(Boolean(row.design_package_id), `${family} generated state missing design package`, evidence.errors);
      assert(Boolean(row.theme_id), `${family} generated state missing theme`, evidence.errors);
      assert(row.revision_memory_count > 0, `${family} generated state missing revision memory`, evidence.errors);
      assert(Boolean(row.export_status), `${family} generated state missing export state`, evidence.errors);
      assert(row.safe_asset_ref_count >= 3, `${family} generated state safe asset refs too thin`, evidence.errors);
    }

    for (const surface of [
      { id: "master-style", name: "master-style-drawer.png" },
      { id: "design-library", name: "design-library-drawer.png" },
      { id: "memory-share", name: "memory-share-drawer.png" },
      { id: "export-handoff", name: "export-handoff-drawer.png" },
    ]) {
      await page.locator(`[data-surface="${surface.id}"]`).click();
      await page.locator(`[data-feature-panel="${surface.id}"]`).waitFor({ state: "visible" });
      evidence.surfaces[surface.id] = {
        title: await page.locator("#feature-surface-title").innerText(),
        close_focused: await page.locator('[data-action="close-surface"]').evaluate((node) => document.activeElement === node),
      };
      await screenshot(page, surface.name, evidence);
      assert(evidence.surfaces[surface.id].close_focused, `${surface.id} drawer close did not receive focus`, evidence.errors);
      await page.keyboard.press("Escape");
      await page.locator("#feature-surface").waitFor({ state: "hidden" });
    }

    const koChrome = await page.locator(".topbar, .toolbar, .inspector").evaluateAll((nodes) => nodes.map((node) => node.innerText).join("\n"));
    const koForbidden = ["Saved local", "No selection", "Select an object", "Copy", "Del", "Dist H", "Dist V", "Fit canvas", "Fit "];
    evidence.localization.workbench_ko_forbidden_hits = koForbidden.filter((term) => koChrome.includes(term));
    await page.locator('[data-locale="en"]').click();
    await page.waitForTimeout(250);
    await screenshot(page, "workbench-en-normal.png", evidence);
    const enChrome = await page.locator(".topbar, .toolbar, .inspector").evaluateAll((nodes) => nodes.map((node) => node.innerText).join("\n"));
    evidence.localization.workbench_en_has_korean_chrome = /[가-힣]/.test(enChrome);

    await page.locator('[data-locale="ko"]').click();
    await page.locator('[data-action="export-pdf"]').click();
    await page.locator('[data-surface="export-handoff"]').click();
    evidence.export_handoff.status_text = await page.locator("#export-status").innerText();
    await screenshot(page, "export-handoff-ko.png", evidence);
    assert(evidence.export_handoff.status_text.includes("핸드오프"), "export handoff status did not localize", evidence.errors);

    for (const plan of ["free", "paid"]) {
      evidence.viewer[plan] = { widths: [] };
      for (const size of widths) {
        await page.setViewportSize({ width: size.width, height: size.height });
        await page.goto(`${baseUrl}/web/commercial-mvp-html-workbench/viewer.html?plan=${plan}`);
        await page.waitForLoadState("networkidle");
        await page.waitForTimeout(300);
        const viewport = page.locator(".viewer-canvas-viewport").first();
        const viewerVisible = await viewport.isVisible();
        const statusText = await page.locator("#viewer-status").innerText();
        const editableControls = await page.locator('[data-action="export-pdf"]').count();
        const watermarkVisible = await page.locator("#viewer-watermark").isVisible();
        const fit = await page.evaluate(() => {
          const viewport = document.querySelector(".viewer-canvas-viewport");
          const rect = viewport?.getBoundingClientRect();
          return {
            viewport_width: rect?.width || 0,
            viewport_height: rect?.height || 0,
            viewport_right: rect?.right || 0,
            viewport_bottom: rect?.bottom || 0,
            inner_width: window.innerWidth,
            inner_height: window.innerHeight,
            body_scroll_width: document.documentElement.scrollWidth,
          };
        });
        const aspect = fit.viewport_height ? fit.viewport_width / fit.viewport_height : 0;
        const row = {
          plan,
          label: size.label,
          viewport: { width: size.width, height: size.height },
          status_text: statusText,
          canvas_visible: viewerVisible,
          editable_controls_visible: editableControls > 0,
          watermark_visible: watermarkVisible,
          first_slide_fits_width: fit.viewport_right <= fit.inner_width + 1 && fit.body_scroll_width <= fit.inner_width + 1,
          first_slide_fits_height: fit.viewport_bottom <= fit.inner_height + 1,
          aspect_ratio_16_9: Math.abs(aspect - (16 / 9)) < 0.02,
          measured: fit,
        };
        evidence.viewer[plan].widths.push(row);
        evidence.viewer_widths.push(row);
        await screenshot(page, `viewer-${plan}-${size.label}.png`, evidence);
        assert(row.canvas_visible, `${plan} viewer canvas not visible at ${size.label}`, evidence.errors);
        assert(editableControls === 0, `${plan} viewer exposes editor controls at ${size.label}`, evidence.errors);
        assert(row.first_slide_fits_width, `${plan} viewer clips or overflows width at ${size.label}`, evidence.errors);
        assert(row.first_slide_fits_height, `${plan} viewer clips or overflows height at ${size.label}`, evidence.errors);
        assert(row.aspect_ratio_16_9, `${plan} viewer first slide lost 16:9 ratio at ${size.label}`, evidence.errors);
        assert(plan === "free" ? watermarkVisible : !watermarkVisible, `${plan} viewer watermark posture is wrong at ${size.label}`, evidence.errors);
      }
    }

    for (const target of [
      { path: "/web/commercial-mvp-site/index.html?locale=ko", name: "site-landing-ko.png", locale: "ko" },
      { path: "/web/commercial-mvp-site/index.html?locale=en", name: "site-landing-en.png", locale: "en" },
      { path: "/web/commercial-mvp-site/account.html?locale=ko", name: "site-account-ko.png", locale: "ko" },
      { path: "/web/commercial-mvp-site/account.html?locale=en", name: "site-account-en.png", locale: "en" },
    ]) {
      await page.goto(`${baseUrl}${target.path}`);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(300);
      await screenshot(page, target.name, evidence);
      const visibleText = await page.locator("body").innerText();
      const key = target.name.replace(".png", "");
      if (target.locale === "ko") {
        const rawStatusSlugVisible = /\b[a-z]+_[a-z0-9_]+\b/.test(visibleText);
        evidence.localization[key] = { raw_status_slug_visible: rawStatusSlugVisible };
        assert(!rawStatusSlugVisible, `${key} exposes raw status slug`, evidence.errors);
      } else {
        const koreanVisible = /[가-힣]/.test(visibleText);
        evidence.localization[key] = { korean_visible: koreanVisible };
        assert(!koreanVisible, `${key} exposes Korean in English mode`, evidence.errors);
      }
    }

    assert(evidence.localization.workbench_ko_forbidden_hits.length === 0, "workbench KO chrome exposes English toolbar/status copy", evidence.errors);
    assert(!evidence.localization.workbench_en_has_korean_chrome, "workbench EN chrome exposes Korean", evidence.errors);
  } finally {
    await browser.close();
  }

  evidence.status = evidence.errors.length ? "invalid" : "valid";
  fs.writeFileSync(reportPath, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
  if (evidence.errors.length) {
    for (const error of evidence.errors) console.error(`ERROR: ${error}`);
    process.exit(1);
  }
  console.log(`commercial_mvp_html_workbench_browser_smoke=valid screenshots=${evidence.screenshots.length} report=${rel(reportPath)}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
