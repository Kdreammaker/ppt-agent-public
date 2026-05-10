const VIEWER_DATA_URL = "./viewer-data.json";
const CANVAS_WIDTH = 1600;
const CANVAS_HEIGHT = 900;

const params = new URLSearchParams(window.location.search);
const plan = params.get("plan") === "paid" ? "paid" : "free";
document.querySelector(".published-viewer").dataset.plan = plan;

function updateViewerScales() {
  const topbar = document.querySelector(".viewer-topbar");
  const stage = document.querySelector(".viewer-stage");
  const slideLabel = document.querySelector(".viewer-slide-label");
  const topbarHeight = topbar?.getBoundingClientRect().height || 0;
  const stageRect = stage?.getBoundingClientRect();
  const stageStyle = stage ? window.getComputedStyle(stage) : null;
  const stagePaddingX = stageStyle ? parseFloat(stageStyle.paddingLeft) + parseFloat(stageStyle.paddingRight) : 36;
  const stagePaddingY = stageStyle ? parseFloat(stageStyle.paddingTop) + parseFloat(stageStyle.paddingBottom) : 24;
  const labelHeight = slideLabel?.getBoundingClientRect().height || 18;
  const viewportPadding = 12;
  const availableHeight = Math.max(260, window.innerHeight - topbarHeight - stagePaddingY - labelHeight - viewportPadding);
  document.querySelector(".published-viewer")?.style.setProperty("--viewer-topbar-height", `${Math.ceil(topbarHeight)}px`);
  document.querySelectorAll(".viewer-canvas-viewport").forEach((viewport) => {
    const stageWidth = stageRect?.width || window.innerWidth;
    const availableWidth = Math.max(320, Math.min(window.innerWidth - stagePaddingX, stageWidth - stagePaddingX, CANVAS_WIDTH));
    const scale = Math.min(availableWidth / CANVAS_WIDTH, availableHeight / CANVAS_HEIGHT, 1);
    viewport.style.setProperty("--viewer-scale", String(scale));
    viewport.style.width = `${Math.ceil(CANVAS_WIDTH * scale)}px`;
    viewport.style.height = `${Math.ceil(CANVAS_HEIGHT * scale)}px`;
  });
}

function styleObject(el, object) {
  el.style.left = `${object.x}px`;
  el.style.top = `${object.y}px`;
  el.style.width = `${object.w}px`;
  el.style.height = `${object.h}px`;
  el.style.zIndex = String(object.z || 1);
  if (object.fill) el.style.background = object.fill;
  if (object.stroke) el.style.borderColor = object.stroke;
  if (object.radius !== undefined) el.style.borderRadius = `${object.radius}px`;
  const flipX = object.flipX ? -1 : 1;
  const flipY = object.flipY ? -1 : 1;
  el.style.transform = `rotate(${object.rotation || 0}deg) scale(${flipX}, ${flipY})`;
}

function renderText(object) {
  const el = document.createElement("div");
  el.className = "slide-object slide-text viewer-object";
  styleObject(el, object);
  el.style.color = object.color || "#151515";
  el.style.fontSize = `${object.fontSize || 24}px`;
  el.style.fontWeight = String(object.fontWeight || 500);
  el.style.lineHeight = String(object.lineHeight || 1.2);
  el.textContent = object.text || "";
  return el;
}

function renderShape(object) {
  const el = document.createElement("div");
  el.className = "slide-object slide-shape viewer-object";
  styleObject(el, object);
  el.style.background = object.fill || "transparent";
  el.style.border = `2px solid ${object.stroke || "transparent"}`;
  return el;
}

function renderLine(object) {
  const el = document.createElement("div");
  el.className = "slide-object slide-line viewer-object";
  styleObject(el, object);
  el.style.borderTop = `${object.strokeWidth || 2}px solid ${object.stroke || "#151515"}`;
  return el;
}

function renderImage(object) {
  const el = document.createElement("div");
  el.className = "slide-object slide-image viewer-object";
  styleObject(el, object);
  el.style.backgroundColor = object.fill || "#e8ecea";
  const label = document.createElement("span");
  label.className = "slide-image-label";
  label.textContent = object.label || "safe asset slot";
  el.append(label);
  return el;
}

function renderTable(object) {
  const wrapper = document.createElement("div");
  wrapper.className = "slide-object slide-table viewer-object";
  styleObject(wrapper, object);
  const table = document.createElement("table");
  const tbody = document.createElement("tbody");
  for (const row of object.rows || []) {
    const tr = document.createElement("tr");
    for (const cell of row) {
      const td = document.createElement("td");
      td.textContent = cell;
      tr.append(td);
    }
    tbody.append(tr);
  }
  table.append(tbody);
  wrapper.append(table);
  return wrapper;
}

function renderObject(object) {
  if (object.type === "text") return renderText(object);
  if (object.type === "shape") return renderShape(object);
  if (object.type === "image") return renderImage(object);
  if (object.type === "table") return renderTable(object);
  if (object.type === "line") return renderLine(object);
  return renderShape(object);
}

function renderViewer(data) {
  document.querySelector("#viewer-title").textContent = data.safe_deck_label;
  const status = document.querySelector("#viewer-status");
  status.textContent = plan === "paid" ? "read-only / watermark-free" : "read-only / free attribution";
  document.querySelector("#viewer-watermark").hidden = plan === "paid";
  const root = document.querySelector("#viewer-slides");
  root.replaceChildren();
  for (const slide of data.slides) {
    const shell = document.createElement("article");
    shell.className = "viewer-slide-shell";
    const viewport = document.createElement("div");
    viewport.className = "viewer-canvas-viewport";
    const canvas = document.createElement("div");
    canvas.className = "slide-canvas viewer-canvas";
    canvas.style.background = slide.background || "#ffffff";
    canvas.style.setProperty("--canvas-scale", "1");
    canvas.setAttribute("aria-label", slide.title || "Published slide");
    for (const object of [...slide.objects].sort((a, b) => (a.z || 0) - (b.z || 0))) {
      canvas.append(renderObject(object));
    }
    viewport.append(canvas);
    const label = document.createElement("p");
    label.className = "viewer-slide-label";
    label.textContent = `${slide.page_label} / ${slide.title}`;
    shell.append(viewport, label);
    root.append(shell);
  }
  updateViewerScales();
}

window.addEventListener("resize", updateViewerScales);

fetch(VIEWER_DATA_URL)
  .then((response) => response.json())
  .then((data) => {
    if (data.schema_version !== "commercial_mvp_published_viewer.v1") {
      throw new Error("viewer payload schema mismatch");
    }
    if (data.read_only !== true || data.editing_api_exposed === true) {
      throw new Error("viewer payload must be read-only");
    }
    renderViewer(data);
  })
  .catch((error) => {
    document.querySelector("#viewer-slides").textContent = `Viewer failed to load: ${error.message}`;
  });
