const SUPPORTED_LOCALES = ["en", "ko"];
const DEFAULT_LOCALE = "ko";

const getNested = (object, path) => path.split(".").reduce((value, key) => value?.[key], object);

const text = (value) => {
  if (value === true) return "true";
  if (value === false) return "false";
  if (value === null || value === undefined) return "not set";
  return String(value);
};

const interpolate = (template, values) =>
  Object.entries(values).reduce((copy, [key, value]) => copy.replaceAll(`{${key}}`, text(value)), template);

const localizedText = (locale, value) => {
  const raw = text(value);
  return locale.valueLabels?.[raw] || raw;
};

const selectedLocale = () => {
  const params = new URLSearchParams(window.location.search);
  const candidate = params.get("locale") || params.get("lang") || DEFAULT_LOCALE;
  return SUPPORTED_LOCALES.includes(candidate) ? candidate : DEFAULT_LOCALE;
};

const loadLocale = async (localeName) => {
  const response = await fetch(`./locales/${localeName}.json`, { cache: "no-store" });
  if (!response.ok) throw new Error(`locale unavailable: ${localeName}`);
  return response.json();
};

const applyLocale = (locale) => {
  document.documentElement.lang = SUPPORTED_LOCALES.includes(locale.locale) ? locale.locale : DEFAULT_LOCALE;
  document.title = document.body.dataset.page === "account" ? locale.documentTitles.account : locale.documentTitles.landing;
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    const value = getNested(locale, node.dataset.i18n);
    if (value) node.textContent = value;
  });
  document.querySelectorAll("[data-i18n-attr]").forEach((node) => {
    const [attribute, key] = node.dataset.i18nAttr.split(":");
    const value = getNested(locale, key);
    if (attribute && value) node.setAttribute(attribute, value);
  });
  document.querySelectorAll("[data-locale-switch]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.localeSwitch === locale.locale));
  });
};

const wireLocaleSwitch = () => {
  document.querySelectorAll("[data-locale-switch]").forEach((button) => {
    button.addEventListener("click", () => {
      const url = new URL(window.location.href);
      url.searchParams.set("locale", button.dataset.localeSwitch);
      window.location.href = url.toString();
    });
  });
};

const statusClass = (value) => {
  const normalized = text(value);
  if (normalized.includes("blocked")) return "status-warning";
  if (normalized.includes("not_attached") || normalized.includes("not_deployed")) return "status-warning";
  if (normalized.includes("limited") || normalized.includes("preview") || normalized.includes("watermarked")) return "status-warning";
  if (normalized.includes("paid") || normalized.includes("included") || normalized.includes("watermark_free")) return "status-yellow";
  if (normalized.includes("leader_only") || normalized.includes("local_static")) return "status-yellow";
  return "status-muted";
};

const addFlag = (root, label, value, locale) => {
  const item = document.createElement("div");
  item.className = "flag";
  item.innerHTML = `<div class="flag-label"></div><div class="flag-value"></div>`;
  item.querySelector(".flag-label").textContent = label;
  item.querySelector(".flag-value").textContent = localizedText(locale || {}, value);
  root.append(item);
};

const renderModes = (data, locale) => {
  const root = document.querySelector("#mode-summary");
  if (!root) return;
  root.replaceChildren();
  addFlag(root, locale.labels.defaultMode, data.product_boundary.default_mode, locale);
  addFlag(root, locale.labels.modes, data.product_boundary.modes.join(", "), locale);
  addFlag(root, locale.labels.hostedGeneration, data.product_boundary.hosted_generation_enabled, locale);
  addFlag(root, locale.labels.backendAi, data.product_boundary.backend_ai_authoring_enabled, locale);
};

const renderStack = (data, locale) => {
  const root = document.querySelector("#stack-summary");
  if (!root) return;
  root.replaceChildren();
  Object.entries(data.commercial_stack_direction).forEach(([key, value]) => {
    addFlag(root, getNested(locale.stackLabels, key) || key, value, locale);
  });
};

const renderPlans = (data, locale) => {
  const root = document.querySelector("#plan-cards");
  if (!root) return;
  root.replaceChildren();
  data.plan_teaser.forEach((plan) => {
    const item = document.createElement("article");
    item.className = "plan-card";
    item.innerHTML = `
      <div class="plan-topline">
        <div class="plan-name"></div>
        <span class="status-pill"></span>
      </div>
      <p class="plan-meta"></p>
      <div class="flag-grid compact"></div>
    `;
    item.querySelector(".plan-name").textContent = plan.tier === "free" ? "Free" : "Paid";
    const pill = item.querySelector(".status-pill");
    pill.textContent = localizedText(locale, plan.status);
    pill.classList.add(statusClass(plan.status));
    item.querySelector(".plan-meta").textContent = interpolate(locale.planCopy.summary, {
      status: localizedText(locale, plan.credit_policy),
    });
    const grid = item.querySelector(".flag-grid");
    [
      [locale.labels.editorAccess, plan.editor_access],
      [locale.labels.viewerSharing, plan.viewer_sharing],
      [locale.labels.referenceDesignLibrary, plan.reference_design_library],
      [locale.labels.styleMemory, plan.style_memory],
      [locale.labels.assetDesignPackages, plan.asset_design_packages],
    ].forEach(([label, value]) => addFlag(grid, label, value, locale));
    root.append(item);
  });
};

const renderAccountFields = (data, locale) => {
  const root = document.querySelector("#account-fields");
  if (!root) return;
  root.replaceChildren();
  const fields = data.account_entry_placeholder.display_fields;
  Object.entries(fields).forEach(([key, value]) => {
    addFlag(root, getNested(locale.accountFieldLabels, key) || key, value, locale);
  });
  addFlag(root, locale.labels.loginImplemented, data.account_entry_placeholder.login_implemented, locale);
  addFlag(root, locale.labels.paymentAttached, data.account_entry_placeholder.payment_attached, locale);
  addFlag(root, locale.labels.hostedSync, data.account_entry_placeholder.hosted_dashboard_sync_enabled, locale);
};

const render = (data, locale) => {
  applyLocale(locale);
  renderModes(data, locale);
  renderStack(data, locale);
  renderPlans(data, locale);
  renderAccountFields(data, locale);
};

Promise.all([
  fetch("./public-site-data.json", { cache: "no-store" }).then((response) => response.json()),
  loadLocale(selectedLocale()),
])
  .then(([data, locale]) => {
    wireLocaleSwitch();
    render(data, locale);
  })
  .catch((error) => {
    console.error("A.DreamMaker public site data load failed", error);
  });
