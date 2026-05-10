import { access, readFile, writeFile } from "node:fs/promises";

const required = [
  "index.html",
  "viewer.html",
  "styles.css",
  "workbench.js",
  "viewer.js",
  "workbench-data.json",
  "generated-work-state.example.json",
  "generated-work-states/ir-final_user_test_polish.json",
  "generated-work-states/sales-final_user_test_polish.json",
  "generated-work-states/portfolio-final_user_test_polish.json",
  "locales/en.json",
  "locales/ko.json",
];

for (const file of required) {
  await access(new URL(`../${file}`, import.meta.url));
}

const [html, css, js, dataRaw] = await Promise.all([
  readFile(new URL("../index.html", import.meta.url), "utf8"),
  readFile(new URL("../styles.css", import.meta.url), "utf8"),
  readFile(new URL("../workbench.js", import.meta.url), "utf8"),
  readFile(new URL("../workbench-data.json", import.meta.url), "utf8"),
]);
const generatedStateRaw = await readFile(new URL("../generated-work-state.example.json", import.meta.url), "utf8");
const generatedFamilyStateRaws = await Promise.all([
  readFile(new URL("../generated-work-states/ir-final_user_test_polish.json", import.meta.url), "utf8"),
  readFile(new URL("../generated-work-states/sales-final_user_test_polish.json", import.meta.url), "utf8"),
  readFile(new URL("../generated-work-states/portfolio-final_user_test_polish.json", import.meta.url), "utf8"),
]);
const viewerHtml = await readFile(new URL("../viewer.html", import.meta.url), "utf8");
const viewerJs = await readFile(new URL("../viewer.js", import.meta.url), "utf8");

const data = JSON.parse(dataRaw);
const generatedState = JSON.parse(generatedStateRaw);
const generatedFamilyStates = generatedFamilyStateRaws.map((raw) => JSON.parse(raw));
const combined = `${html}\n${viewerHtml}\n${css}\n${js}\n${viewerJs}\n${dataRaw}\n${generatedStateRaw}\n${generatedFamilyStateRaws.join("\n")}`;
const forbidden = [
  ["Authorization", ":"].join(""),
  ["Bearer", " "].join(""),
  ["api", "_", "key"].join(""),
  ["data", ":", "image"].join(""),
  "UEs" + "DB",
  "DOMParser",
  ["complete", " export"].join(""),
  ["export", " complete"].join(""),
];

const hits = forbidden.filter((marker) => combined.includes(marker));
if (hits.length) {
  throw new Error(`forbidden marker in HTML workbench surface: ${hits.join(", ")}`);
}

if (data.schema_version !== "commercial_mvp_html_workbench.v1") {
  throw new Error("workbench data schema mismatch");
}
if (data.fixture_metadata?.is_fixture !== true || data.fixture_metadata?.not_benchmark_copy !== true) {
  throw new Error("workbench fixture metadata must be explicit");
}
if (data.generated_work_state_loading?.separate_from_fixture_data !== true || generatedState.source_kind !== "host_ai_generated_work_state") {
  throw new Error("generated work-state loader must stay separate from fixture data");
}
for (const state of generatedFamilyStates) {
  if (state.source_kind !== "host_ai_generated_work_state" || state.fixture !== false || state.fixture_metadata?.is_fixture !== false) {
    throw new Error(`generated family state must be non-fixture: ${state.deck_id || "unknown"}`);
  }
  if (!state.design_package?.design_package_id || !state.theme_tokens?.theme_id || !state.revision_memory?.length) {
    throw new Error(`generated family state missing design/theme/revision evidence: ${state.deck_id || "unknown"}`);
  }
  if (state.export_hooks?.current_status !== "handoff_ready" || state.export_hooks?.real_host_result_ref !== null) {
    throw new Error(`generated family state must keep honest export status: ${state.deck_id || "unknown"}`);
  }
  if (!Array.isArray(state.safe_asset_refs) || state.safe_asset_refs.length < 3) {
    throw new Error(`generated family state safe asset refs missing: ${state.deck_id || "unknown"}`);
  }
}
for (const key of ["design_package", "theme_tokens", "master_styles", "text_style_roles", "layout_recipes", "component_recipes", "revision_memory"]) {
  if (!data[key]) throw new Error(`workbench missing V2 state field: ${key}`);
}
for (const key of ["reference_design_library", "style_memory_profiles", "published_views", "referral_entitlement", "generated_work_state_loading", "local_asset_connection_ux"]) {
  if (!data[key]) throw new Error(`workbench missing commercial scaffold field: ${key}`);
}
for (const role of ["Title", "H1", "H2", "H3", "Body", "Caption", "Bullet"]) {
  if (!data.text_style_roles[role]) throw new Error(`workbench missing text role: ${role}`);
}
if (data.product_boundary.default_mode !== "assistant") {
  throw new Error("Assistant must remain default");
}
if (new Set(data.product_boundary.modes).size !== 2 || !data.product_boundary.modes.includes("assistant") || !data.product_boundary.modes.includes("auto")) {
  throw new Error("workbench must expose Assistant and Auto only");
}
if (!Array.isArray(data.deck.slides) || data.deck.slides.length < 10) {
  throw new Error("workbench deck must contain at least 10 slides");
}
if (data.export_hooks.allowed_statuses.join("|") !== "handoff_ready|handoff_sent|awaiting_host_ai|proposal_ready|blocked|final_received") {
  throw new Error("export hook status model mismatch");
}
if (data.export_hooks.result_return_handling?.final_received_requires_real_result_ref !== true) {
  throw new Error("final_received must require a real result reference");
}
for (const marker of [
  "beginInlineTextEdit",
  "commitInlineTextEdit",
  "startObjectDrag",
  "startResize",
  "duplicateSelectedObject",
  "deleteSelectedObject",
  "changeZOrder",
  "applyRichTextPatch",
  "toggleBullet",
  "selectedObjectIds",
  "distributeSelected",
  "transformSelected",
  "loadGeneratedWorkbenchState",
  "validateGeneratedWorkbenchInput",
  "createExportEnvelope",
  "data-dev-diagnostics",
]) {
  if (!combined.includes(marker)) {
    throw new Error(`workbench missing required behavior marker: ${marker}`);
  }
}

const viewerPayload = {
  schema_version: "commercial_mvp_published_viewer.v1",
  view_id: data.published_views?.[0]?.view_id,
  deck_version_id: data.published_views?.[0]?.deck_version_id,
  safe_deck_label: data.deck.safe_label,
  canvas: data.deck.canvas,
  read_only: true,
  editing_api_exposed: false,
  raw_workbench_state_exposed: false,
  raw_asset_urls_exposed: false,
  package_internals_exposed: false,
  watermark: {
    free: "made_with_attribution",
    paid: "none",
  },
  slides: data.deck.slides.map((slide, index) => ({
    id: slide.id,
    title: slide.title,
    page_label: String(index + 1).padStart(2, "0"),
    background: slide.background || "#FFFFFF",
    objects: slide.objects.map((object) => {
      const base = {
        id: object.id,
        type: object.type,
        x: object.x,
        y: object.y,
        w: object.w,
        h: object.h,
        z: object.z,
        fill: object.fill,
        stroke: object.stroke,
        radius: object.radius,
        rotation: object.rotation || 0,
        flipX: Boolean(object.flipX),
        flipY: Boolean(object.flipY),
      };
      if (object.type === "text") {
        return {
          ...base,
          text: object.text,
          fontSize: object.fontSize,
          fontWeight: object.fontWeight,
          color: object.color,
          lineHeight: object.lineHeight,
        };
      }
      if (object.type === "image") {
        return { ...base, label: object.label || "safe asset slot", fit: object.fit };
      }
      if (object.type === "table") {
        return { ...base, rows: object.rows || [] };
      }
      if (object.type === "line") {
        return { ...base, strokeWidth: object.strokeWidth };
      }
      return base;
    }),
  })),
};

await writeFile(new URL("../viewer-data.json", import.meta.url), `${JSON.stringify(viewerPayload, null, 2)}\n`, "utf8");

console.log(`commercial-mvp-html-workbench build ok: slides=${data.deck.slides.length} viewer=ready`);
