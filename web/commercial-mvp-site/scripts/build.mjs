import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const projectDir = resolve(scriptDir, "..");
const required = [
  "index.html",
  "account.html",
  "styles.css",
  "site.js",
  "public-site-data.json",
  "locales/en.json",
  "locales/ko.json",
  "vercel.json",
];
const forbidden = [
  ["postgresql", "://"].join(""),
  ["postgres", "://"].join(""),
  ["supabase", ".co"].join(""),
  ["corp", "-db", ".local"].join(""),
  ["company", "-postgres", ".local"].join(""),
  ["C", ":", "\\"].join(""),
  ["/", "Users", "/"].join(""),
  ["package", "_manifest"].join(""),
  ["raw", "_evidence", "_root"].join(""),
  ["private", "_prompt"].join(""),
  ["Authorization", ":"].join(""),
  ["Bear", "er "].join(""),
  ["api", "_key"].join(""),
  ["route", "_backed", "_operator", "_actions"].join(""),
  ["duplicate", "_idempotency", "_replay"].join(""),
  ["admin", "_adjust", "_credit"].join(""),
  ["operator", "-dashboard", "-data", ".json"].join(""),
];

let checkedBytes = 0;
for (const relative of required) {
  const text = readFileSync(join(projectDir, relative), "utf8");
  checkedBytes += text.length;
  for (const marker of forbidden) {
    if (text.includes(marker)) {
      throw new Error(`forbidden public-site marker found in ${relative}: ${marker}`);
    }
  }
}

const data = JSON.parse(readFileSync(join(projectDir, "public-site-data.json"), "utf8"));
const en = JSON.parse(readFileSync(join(projectDir, "locales/en.json"), "utf8"));
const ko = JSON.parse(readFileSync(join(projectDir, "locales/ko.json"), "utf8"));

if (data.brand.primary_display !== "A.DreamMaker" || data.brand.full_brand !== "ADOTDREAMMAKER") {
  throw new Error("public site brand mismatch");
}
if (data.product_boundary.default_mode !== "assistant") {
  throw new Error("Assistant must remain default");
}
if (data.product_boundary.modes.join(",") !== "assistant,auto") {
  throw new Error("public site modes must stay Assistant/Auto only");
}
if (data.commercial_stack_direction.payment !== "not_attached") {
  throw new Error("payment must remain unattached");
}
if (data.commercial_stack_direction.vercel_web !== "local_static_skeleton_not_deployed") {
  throw new Error("public site must remain local and not deployed");
}
if (data.account_entry_placeholder.login_implemented !== false) {
  throw new Error("account entry must not implement login");
}
if (data.account_entry_placeholder.payment_attached !== false) {
  throw new Error("account entry must not attach payment");
}
if (data.account_entry_placeholder.hosted_dashboard_sync_enabled !== false) {
  throw new Error("account entry must not sync hosted dashboard");
}
if (data.plan_teaser.length !== 2 || data.plan_teaser.map((plan) => plan.tier).join("|") !== "free|paid") {
  throw new Error("public plan teaser must stay Free plus Paid");
}
if (data.plan_teaser.find((plan) => plan.tier === "paid")?.credit_policy !== "no_visible_per_edit_credit_for_normal_workflows") {
  throw new Error("paid plan must not expose per-edit credit accounting");
}
if (en.locale !== "en" || ko.locale !== "ko") {
  throw new Error("public site locale mismatch");
}

console.log(`commercial_mvp_public_site_frontend_build=passed files=${required.length} bytes=${checkedBytes}`);
