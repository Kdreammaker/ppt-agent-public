const DATA_URL = "./workbench-data.json";
const CANVAS_WIDTH = 1600;
const CANVAS_HEIGHT = 900;
const MIN_OBJECT_SIZE = 32;

const app = {
  data: null,
  deck: null,
  activeSlideIndex: 0,
  selectedObjectId: null,
  selectedObjectIds: [],
  mode: "assistant",
  scale: 1,
  zoomMode: "fit",
  manualZoom: 1,
  locale: "ko",
  theme: "light",
  undoStack: [],
  redoStack: [],
  operationLog: [],
  revisionMemory: [],
  activeExportEnvelope: null,
  exportMessageKey: "handoff_ready",
  baselineStyleData: null,
  drag: null,
  resize: null,
  editingObjectId: null,
  activeTextSelection: null,
  inlineEditKeyHandler: null,
  inlineEditBlurHandler: null,
  feedbackTimer: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

const refs = {
  deckLabel: $("#deck-label"),
  slideCount: $("#slide-count"),
  slideList: $("#slide-list"),
  slideTitle: $("#slide-title"),
  modeNote: $("#mode-note"),
  workStateSummary: $("#work-state-summary"),
  canvasFrame: $("#canvas-frame"),
  canvasViewport: $("#canvas-viewport"),
  canvas: $("#slide-canvas"),
  featureSurface: $("#feature-surface"),
  featureSurfaceTitle: $("#feature-surface-title"),
  commandFeedback: $("#command-feedback"),
  inspector: $(".inspector"),
  inspectorState: $("#inspector-state"),
  selectedLabel: $("#selected-label"),
  saveStatus: $("#save-status"),
  exportStatus: $("#export-status"),
  exportSummary: $("#export-summary"),
  operationLog: $("#operation-log"),
  handoffEnvelope: $("#handoff-envelope"),
  textEditor: $("#text-editor"),
  textRole: $("#text-role"),
  textFont: $("#text-font"),
  textSize: $("#text-size"),
  textColor: $("#text-color"),
  alignTarget: $("#align-target"),
  shapeRadius: $("#shape-radius"),
  masterPalette: $("#master-palette"),
  masterTypeScale: $("#master-type-scale"),
  masterRadius: $("#master-radius"),
  zoomLabel: $("#zoom-label"),
  styleSummary: $("#style-summary"),
  revisionMemory: $("#revision-memory"),
  referenceLibrary: $("#reference-library"),
  referenceApplySummary: $("#reference-apply-summary"),
  styleMemory: $("#style-memory"),
  publishedView: $("#published-view"),
  referralCredit: $("#referral-credit"),
  localAssets: $("#local-assets"),
  objectStyleSummary: $("#object-style-summary"),
  geometry: {
    x: $("#prop-x"),
    y: $("#prop-y"),
    w: $("#prop-w"),
    h: $("#prop-h"),
  },
};

const MASTER_STYLE_PRESETS = {
  baseline: {
    label: "Neutral yellow",
    koLabel: "뉴트럴 옐로",
    palette: { canvas: "#FFFFFF", surface: "#F7F5EF", ink: "#151515", muted: "#576267", accent: "#F2D76B", deep: "#132326" },
  },
  contrast: {
    label: "High contrast",
    koLabel: "고대비",
    palette: { canvas: "#FFFFFF", surface: "#EEF2F3", ink: "#101314", muted: "#465054", accent: "#2B77FF", deep: "#0F1C22" },
  },
  editorial: {
    label: "Editorial green",
    koLabel: "에디토리얼 그린",
    palette: { canvas: "#FFFFFF", surface: "#F4F7F2", ink: "#16201C", muted: "#52635A", accent: "#9FD4B3", deep: "#183D31" },
  },
};

const TYPE_SCALE_PRESETS = {
  compact: { label: "Compact", koLabel: "압축", multiplier: 0.92 },
  standard: { label: "Standard", koLabel: "표준", multiplier: 1 },
  spacious: { label: "Spacious", koLabel: "여유", multiplier: 1.08 },
};

const UI_TEXT = {
  ko: {
    deckSurface: "덱 표면",
    close: "닫기",
    buttons: {
      toggleTheme: "라이트/다크",
      masterStyle: "마스터 스타일",
      designLibrary: "디자인 라이브러리",
      memoryShare: "메모리 / 공유",
      exportPdf: "PDF 내보내기",
      exportPptx: "PPTX 내보내기",
      exportStatus: "내보내기 상태",
      applyText: "텍스트 적용",
      importRecipes: "디자인 레시피 가져오기",
      applyRecipe: "레시피 적용",
      resetRecipe: "레시피 되돌리기",
      proposalReady: "제안 준비됨",
      blocked: "차단됨",
      finalReceived: "최종 수신",
    },
    mode: {
      assistant: "어시스턴트",
      auto: "자동",
      assistantNote: "어시스턴트는 기본 생성/수정 흐름입니다.",
      autoNote: "자동은 두 후보 방향을 슬라이드 레일 밖에서 비교합니다.",
    },
    surfaces: {
      "master-style": "마스터 스타일",
      "design-library": "디자인 라이브러리",
      "memory-share": "메모리와 게시 뷰어",
      "export-handoff": "내보내기 핸드오프",
    },
    actions: {
      undo: ["실행 취소", "↶"],
      redo: ["다시 실행", "↷"],
      "text-bold": ["굵게", "B"],
      "text-bullet": ["문단 글머리표", "•"],
      "align-text-left": ["텍스트 왼쪽 정렬", "L"],
      "align-text-center": ["텍스트 가운데 정렬", "C"],
      "align-text-right": ["텍스트 오른쪽 정렬", "R"],
      "duplicate-object": ["복제", "복제"],
      "delete-object": ["삭제", "삭제"],
      "bring-forward": ["앞으로 가져오기", "↑"],
      "send-backward": ["뒤로 보내기", "↓"],
      "align-left": ["왼쪽 정렬", "|L"],
      "align-center": ["가운데 정렬", "|C"],
      "align-right": ["오른쪽 정렬", "R|"],
      "align-top": ["위쪽 정렬", "T"],
      "align-middle": ["중앙 정렬", "M"],
      "align-bottom": ["아래쪽 정렬", "B"],
      "distribute-horizontal": ["가로 분배", "가로분배"],
      "distribute-vertical": ["세로 분배", "세로분배"],
      "rotate-minus-15": ["15도 반시계 회전", "-15"],
      "rotate-plus-15": ["15도 시계 회전", "+15"],
      "rotate-minus-90": ["90도 반시계 회전", "-90"],
      "rotate-plus-90": ["90도 시계 회전", "+90"],
      "rotate-reset": ["회전 초기화", "0"],
      "flip-horizontal": ["좌우 뒤집기", "좌우"],
      "flip-vertical": ["상하 뒤집기", "상하"],
      "zoom-out": ["축소", "−"],
      "zoom-fit": ["캔버스 맞춤", "맞춤"],
      "zoom-in": ["확대", "+"],
      "add-text": ["텍스트 상자 추가", "T+"],
      "add-shape": ["도형 추가", "□+"],
      "apply-reference-recipe": ["레시피 적용", "적용"],
      "reset-reference-recipe": ["레시피 되돌리기", "되돌리기"],
    },
    labels: {
      role: "역할",
      font: "글꼴",
      size: "크기",
      color: "색상",
      radius: "반경",
      alignTo: "정렬 기준",
      slides: "슬라이드",
      canvas: "HTML 슬라이드 캔버스",
      properties: "속성",
      positionSize: "위치와 크기",
      text: "텍스트",
      resolvedStyle: "적용된 스타일",
      noSelection: "선택 없음",
      saved: "로컬 저장됨",
      selectObject: "오브젝트를 선택해 텍스트, 위치, 변환을 조정하세요.",
      multiSelection: "여러 오브젝트를 선택했습니다. 정렬/분배와 공통 경계 상자를 사용할 수 있으며 단일 텍스트 편집은 꺼집니다.",
      textSelection: "텍스트 오브젝트를 선택했습니다. 캔버스를 두 번 클릭해 직접 편집하거나 텍스트 도구를 사용하세요.",
      shapeSelection: "도형을 선택했습니다. 위치, 레이어, 고정 회전, 뒤집기, 모서리 반경을 조정할 수 있습니다.",
      imageSelection: "이미지 슬롯을 선택했습니다. 위치, 레이어, 고정 회전, 뒤집기를 조정할 수 있습니다.",
      tableSelection: "표를 선택했습니다. 위치와 레이어를 조정할 수 있으며 셀 편집은 다음 단계입니다.",
      lineSelection: "선을 선택했습니다. 위치와 레이어를 조정할 수 있으며 도형/이미지 변환은 사용할 수 없습니다.",
      selectedCount: "개 선택됨",
    },
    status: {
      handoff_ready: "핸드오프 준비",
      handoff_sent: "핸드오프 전송됨",
      awaiting_host_ai: "Host AI 대기 중",
      proposal_ready: "제안 검토 준비",
      blocked: "내보내기 차단",
      final_received: "최종 결과 수신",
    },
    exportMessages: {
      handoff_ready: "PDF/PPTX 요청을 보낼 준비가 되었습니다. 아직 최종 파일은 없습니다.",
      handoff_sent: "현재 작업 요약을 Host AI에 보냈습니다. 결과를 기다립니다.",
      awaiting_host_ai: "Host AI가 최종 파일이나 제안을 만드는 중입니다. 아직 받은 결과는 없습니다.",
      proposal_ready: "Host AI 제안이 도착했습니다. 검토 후 적용하면 현재 작업이 바뀝니다.",
      blocked: "공개 안전한 제안이나 결과가 오기 전까지 완료로 표시하지 않습니다.",
      final_missing: "안전한 최종 결과 참조가 없습니다. 계속 대기 상태로 유지합니다.",
      final_received: "안전한 Host-AI 결과 참조가 확인되어 최종 수신으로 표시합니다.",
    },
  },
  en: {
    deckSurface: "Deck surface",
    close: "Close",
    buttons: {
      toggleTheme: "Light/Dark",
      masterStyle: "Master Style",
      designLibrary: "Design Library",
      memoryShare: "Memory / Share",
      exportPdf: "Export PDF",
      exportPptx: "Export PPTX",
      exportStatus: "Export Status",
      applyText: "Apply text",
      importRecipes: "Import design recipes",
      applyRecipe: "Apply recipe",
      resetRecipe: "Reset recipe",
      proposalReady: "Proposal ready",
      blocked: "Blocked",
      finalReceived: "Final received",
    },
    mode: {
      assistant: "Assistant",
      auto: "Auto",
      assistantNote: "Assistant is the default local editing flow.",
      autoNote: "Auto compares two candidate directions outside the slide rail.",
    },
    surfaces: {
      "master-style": "Master Style",
      "design-library": "Reference Design Library",
      "memory-share": "Memory and Published Viewer",
      "export-handoff": "Export Handoff",
    },
    actions: {
      undo: ["Undo", "↶"],
      redo: ["Redo", "↷"],
      "text-bold": ["Bold", "B"],
      "text-bullet": ["Bullet paragraph", "•"],
      "align-text-left": ["Text align left", "L"],
      "align-text-center": ["Text align center", "C"],
      "align-text-right": ["Text align right", "R"],
      "duplicate-object": ["Duplicate", "Copy"],
      "delete-object": ["Delete", "Del"],
      "bring-forward": ["Bring forward", "↑"],
      "send-backward": ["Send backward", "↓"],
      "align-left": ["Align left", "|L"],
      "align-center": ["Align center", "|C"],
      "align-right": ["Align right", "R|"],
      "align-top": ["Align top", "T"],
      "align-middle": ["Align middle", "M"],
      "align-bottom": ["Align bottom", "B"],
      "distribute-horizontal": ["Distribute horizontal", "Dist H"],
      "distribute-vertical": ["Distribute vertical", "Dist V"],
      "rotate-minus-15": ["Rotate -15 degrees", "-15"],
      "rotate-plus-15": ["Rotate +15 degrees", "+15"],
      "rotate-minus-90": ["Rotate -90 degrees", "-90"],
      "rotate-plus-90": ["Rotate +90 degrees", "+90"],
      "rotate-reset": ["Reset rotation", "0"],
      "flip-horizontal": ["Flip horizontal", "Flip H"],
      "flip-vertical": ["Flip vertical", "Flip V"],
      "zoom-out": ["Zoom out", "−"],
      "zoom-fit": ["Fit canvas", "Fit"],
      "zoom-in": ["Zoom in", "+"],
      "add-text": ["Add text box", "T+"],
      "add-shape": ["Add shape", "□+"],
      "apply-reference-recipe": ["Apply recipe", "Apply"],
      "reset-reference-recipe": ["Reset recipe", "Reset"],
    },
    labels: {
      role: "Role",
      font: "Font",
      size: "Size",
      color: "Color",
      radius: "Radius",
      alignTo: "Align to",
      slides: "Slides",
      canvas: "HTML slide canvas",
      properties: "Properties",
      positionSize: "Position and size",
      text: "Text",
      resolvedStyle: "Resolved style",
      noSelection: "No selection",
      saved: "Saved local",
      selectObject: "Select an object to edit text, geometry, or transforms.",
      multiSelection: "Multiple objects selected. Use align/distribute and shared bounding-box reference; single-object text editing is disabled.",
      textSelection: "Text object selected. Double-click the canvas for direct editing or use the text controls.",
      shapeSelection: "Shape selected. Geometry, z-order, fixed rotation, flip, and corner radius are available.",
      imageSelection: "Image slot selected. Geometry, z-order, fixed rotation, and flip are available.",
      tableSelection: "Table selected. Geometry and z-order are available; table cell editing is deferred.",
      lineSelection: "Line selected. Geometry and z-order are available; shape/image transforms are unavailable.",
      selectedCount: "selected",
    },
    status: {
      handoff_ready: "Handoff ready",
      handoff_sent: "Handoff sent",
      awaiting_host_ai: "Awaiting host AI",
      proposal_ready: "Proposal ready",
      blocked: "Export blocked",
      final_received: "Final received",
    },
    exportMessages: {
      handoff_ready: "Ready to ask host AI for a PDF/PPTX. No final file has been received.",
      handoff_sent: "Current work summary sent to host AI. Waiting for a result.",
      awaiting_host_ai: "Host AI is still preparing a file or proposal. Nothing final has been received.",
      proposal_ready: "A host-AI proposal is ready for review. Applying it changes the local work state.",
      blocked: "PPT Maker will not mark this complete until a public-safe proposal or result arrives.",
      final_missing: "No safe final result reference is available. PPT Maker will keep waiting.",
      final_received: "A safe host-AI result reference has been verified.",
    },
  },
};

const REFERENCE_FAMILY_CARDS = {
  ir: {
    label: "IR",
    koLabel: "IR",
    tone: "Investor-ready hierarchy",
    koTone: "투자 검토용 정보 위계",
  },
  sales: {
    label: "Sales",
    koLabel: "세일즈",
    tone: "Conversion and proof flow",
    koTone: "전환과 근거 중심 흐름",
  },
  portfolio: {
    label: "Portfolio",
    koLabel: "포트폴리오",
    tone: "Visual case-led pacing",
    koTone: "시각 사례 중심 리듬",
  },
};

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function activeSlide() {
  return app.deck.slides[app.activeSlideIndex];
}

function selectedObject() {
  const slide = activeSlide();
  return slide?.objects.find((object) => object.id === app.selectedObjectId) || null;
}

function selectedObjects() {
  const slide = activeSlide();
  if (!slide) return [];
  return app.selectedObjectIds
    .map((id) => slide.objects.find((object) => object.id === id))
    .filter(Boolean);
}

function isTextEntryTarget(target) {
  const element = target instanceof Element ? target : null;
  if (!element) return false;
  if (element.closest("[contenteditable='true']")) return true;
  const tagName = element.tagName;
  return tagName === "INPUT" || tagName === "TEXTAREA" || tagName === "SELECT";
}

function setSelection(ids) {
  const unique = [...new Set(ids.filter(Boolean))];
  app.selectedObjectIds = unique;
  app.selectedObjectId = unique[unique.length - 1] || null;
}

function plainText(object) {
  if (object?.paragraphs?.length) {
    return object.paragraphs
      .map((paragraph) => (paragraph.runs || []).map((run) => run.text || "").join(""))
      .join("\n");
  }
  return object?.text || "";
}

function inferTextRole(object) {
  if (object.textRole) return object.textRole;
  if (object.id?.includes("page")) return "Caption";
  if ((object.fontSize || 0) >= 60) return "Title";
  if ((object.fontSize || 0) >= 44) return "H1";
  if ((object.fontSize || 0) >= 36) return "H2";
  if ((object.fontSize || 0) >= 29) return "H3";
  return "Body";
}

function textToParagraphs(text, object = {}) {
  const role = inferTextRole(object);
  const paragraphs = String(text || "")
    .split(/\n{2,}/)
    .map((part) => part.trimEnd())
    .filter((part) => part.length > 0);
  return (paragraphs.length ? paragraphs : [""]).map((part, index) => ({
    role: index > 0 && role === "Body" ? "Bullet" : role,
    alignment: object.textAlign || (object.fill ? "center" : "left"),
    bullet: role === "Bullet" || (index > 0 && object.id?.includes("step")),
    bulletLevel: 0,
    spacingAfter: 4,
    overflowPolicy: "wrap",
    runs: [
      {
        text: part,
        fontFamilyToken: object.fontFamilyToken || (role === "Caption" ? "caption" : role === "Body" ? "body" : "heading"),
        fontSize: object.fontSize || app.data?.text_style_roles?.[role]?.fontSize || 24,
        fontWeight: object.fontWeight || app.data?.text_style_roles?.[role]?.fontWeight || 500,
        color: object.color || app.data?.text_style_roles?.[role]?.color || "#151515",
      },
    ],
  }));
}

function normalizeWorkbenchState(data) {
  const textRoles = data.text_style_roles || {};
  for (const slide of data.deck.slides) {
    slide.master_style_id ||= data.master_styles?.[0]?.master_style_id || "master-style-commercial-mvp-v1";
    slide.theme_id ||= data.theme_tokens?.theme_id || "theme-adreammaker-neutral-yellow-v1";
    slide.layout_recipe_id ||= slide.section === "Opening" ? "cover_title" : "executive_summary";
    slide.component_recipe_id ||= "metric_card";
    slide.token_set_id ||= data.theme_tokens?.token_set_id || "token-set-commercial-mvp-v1";
    for (const object of slide.objects) {
      object.rotation ??= 0;
      object.flipX ??= false;
      object.flipY ??= false;
      object.transformScope ??= object.type === "shape" || object.type === "image" ? "shape_image_fixed_step" : "box_only";
      if (object.type === "text") {
        object.textRole = inferTextRole(object);
        object.paragraphs ||= textToParagraphs(object.text || "", object);
        const roleDefaults = textRoles[object.textRole] || {};
        object.fontFamilyToken ||= roleDefaults.fontFamilyToken || "body";
        object.letterSpacing ??= 0;
      }
    }
  }
  data.revision_memory ||= [];
  return data;
}

function validateGeneratedWorkbenchInput(input) {
  const required = app.data?.generated_work_state_loading?.required_safe_fields || ["deck_id", "safe_label", "canvas", "slides"];
  const missing = required.filter((field) => input?.[field] === undefined && input?.deck?.[field] === undefined);
  const blockedText = JSON.stringify(input || {});
  const blockedFamilies = app.data?.generated_work_state_loading?.blocked_input_families || [];
  const blocked = blockedFamilies.filter((family) => blockedText.includes(family));
  const unsafeRefs = collectUnsafeAssetRefs(input);
  const privateMarkers = ["://", "data:", ["base", "64,"].join(""), "<script", "src=", "href="].filter((marker) => blockedText.toLowerCase().includes(marker));
  return {
    valid: missing.length === 0 && blocked.length === 0 && unsafeRefs.length === 0 && privateMarkers.length === 0,
    missing,
    blocked,
    unsafeRefs,
    privateMarkers,
  };
}

function collectUnsafeAssetRefs(value, found = []) {
  if (!value || typeof value !== "object") return found;
  if (Array.isArray(value)) {
    value.forEach((item) => collectUnsafeAssetRefs(item, found));
    return found;
  }
  for (const [key, item] of Object.entries(value)) {
    if (key === "safeRef" || key === "safe_asset_ref") {
      const ref = String(item || "");
      if (!ref.startsWith("asset:") || ref.includes("://") || ref.includes("\\") || ref.includes("/")) {
        found.push(ref || "(empty)");
      }
    } else {
      collectUnsafeAssetRefs(item, found);
    }
  }
  return found;
}

function loadGeneratedWorkbenchState(input) {
  const result = validateGeneratedWorkbenchInput(input);
  if (!result.valid) {
    const reason = result.missing.length
      ? `missing ${result.missing.join(", ")}`
      : result.unsafeRefs.length
        ? "unsafe asset references"
        : result.privateMarkers.length
          ? "private or raw content markers"
          : "blocked source markers";
    const friendly = app.locale === "ko"
      ? `생성 작업 상태를 열 수 없습니다. ${reason} 항목을 안전한 값으로 바꿔 주세요.`
      : `This generated work state cannot be opened yet. Please replace ${reason} with safe values.`;
    showCommandFeedback(friendly);
    return { ...result, friendly_message: friendly };
  }
  pushHistory("load generated state");
  const sourceDeck = input.deck || input;
  const generatedKeys = [
    "design_package",
    "theme_tokens",
    "revision_memory",
    "export_hooks",
    "reference_design_library",
    "style_memory_profiles",
    "published_views",
    "asset_system_consumption",
    "safe_asset_refs",
    "local_asset_connection_ux",
    "design_guide_package",
    "master_styles",
    "master_style_surface",
    "text_style_roles",
    "layout_recipes",
    "component_recipes",
  ];
  const fixtureMetadata = {
    is_fixture: false,
    source_kind: "host_ai_generated_work_state",
    not_host_ai_generated_output: false,
    not_benchmark_copy: true,
  };
  const mergedData = {
    ...app.data,
    fixture_metadata: fixtureMetadata,
    deck: clone(sourceDeck),
  };
  for (const key of generatedKeys) {
    if (input[key] !== undefined) mergedData[key] = clone(input[key]);
  }
  app.data = normalizeWorkbenchState(mergedData);
  app.baselineStyleData = {
    theme_tokens: clone(app.data.theme_tokens),
    text_style_roles: clone(app.data.text_style_roles),
    master_styles: clone(app.data.master_styles),
  };
  app.deck = app.data.deck;
  app.revisionMemory = clone(app.data.revision_memory || []);
  app.activeSlideIndex = 0;
  setSelection([]);
  recordOperation("generated_work_state_loaded", { summary: "host-AI generated work state loaded through safe schema path" });
  renderAll();
  return {
    valid: true,
    loaded: true,
    fixture: false,
    deck_id: app.deck.deck_id,
    design_package_id: app.data.design_package?.design_package_id || null,
    theme_id: app.data.theme_tokens?.theme_id || null,
    revision_memory_count: app.revisionMemory.length,
    export_status: app.data.export_hooks?.current_status || null,
    safe_asset_ref_count: countSafeAssetRefs(),
  };
}

function setObjectText(object, text) {
  object.text = text;
  object.paragraphs = textToParagraphs(text, object);
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function pushHistory(label) {
  app.undoStack.push({
    label,
    deck: clone(app.deck),
    activeSlideIndex: app.activeSlideIndex,
    selectedObjectId: app.selectedObjectId,
    selectedObjectIds: clone(app.selectedObjectIds),
  });
  if (app.undoStack.length > 80) app.undoStack.shift();
  app.redoStack = [];
}

function restoreSnapshot(snapshot) {
  app.deck = clone(snapshot.deck);
  app.activeSlideIndex = snapshot.activeSlideIndex;
  setSelection(snapshot.selectedObjectIds || [snapshot.selectedObjectId]);
  renderAll();
  markSaved(`Restored ${snapshot.label}`);
}

function recordOperation(kind, detail = {}) {
  const operation = {
    kind,
    slide_id: activeSlide()?.id || null,
    object_id: detail.object_id || app.selectedObjectId || null,
    object_type: detail.object_type || selectedObject()?.type || null,
    summary: detail.summary || kind,
  };
  app.operationLog.push(operation);
  if (app.operationLog.length > 60) app.operationLog.shift();
  markSaved(UI_TEXT[app.locale].labels.saved);
}

function sanitizedOperationSummary() {
  return app.operationLog.slice(-20).map((operation) => ({
    kind: operation.kind,
    slide_id: operation.slide_id,
    object_id: operation.object_id,
    object_type: operation.object_type,
    summary: operation.summary,
  }));
}

function safeWorkStateReference() {
  const slide = activeSlide();
  const textRoleSummary = {};
  for (const deckSlide of app.deck.slides) {
    for (const object of deckSlide.objects) {
      if (object.type === "text") {
        textRoleSummary[object.textRole || "Body"] = (textRoleSummary[object.textRole || "Body"] || 0) + 1;
      }
    }
  }
  return {
    deck_id: app.deck.deck_id,
    deck_label: app.deck.safe_label,
    selected_slide_id: slide.id,
    slide_count: app.deck.slides.length,
    object_count: slide.objects.length,
    design_guide_version: app.data.design_guide_package.version,
    fixture_metadata: app.data.fixture_metadata,
    design_package: {
      design_package_id: app.data.design_package.design_package_id,
      manifest_hash: app.data.design_package.manifest_hash,
      source_kind: app.data.design_package.source_kind,
      asset_system_package_ref: app.data.design_package.asset_system_package_ref,
    },
    text_role_summary: textRoleSummary,
    paragraph_summary: summarizeParagraphs(),
    transform_summary: summarizeTransforms(),
    revision_memory_summary: app.revisionMemory.slice(-8).map(({ memory_id, kind, mode, summary }) => ({ memory_id, kind, mode, summary })),
    reference_design_library_summary: referenceDesignHandoffSummary(),
    style_memory_summary: styleMemoryHandoffSummary(),
    published_view_summary: publishedViewHandoffSummary(),
    referral_credit_summary: referralCreditHandoffSummary(),
    safe_asset_design_refs: safeAssetDesignRefs(),
    canvas: app.deck.canvas,
  };
}

function summarizeParagraphs() {
  let paragraphCount = 0;
  let bulletCount = 0;
  let richRunCount = 0;
  for (const slide of app.deck.slides) {
    for (const object of slide.objects) {
      if (object.type !== "text") continue;
      paragraphCount += object.paragraphs?.length || 0;
      bulletCount += (object.paragraphs || []).filter((paragraph) => paragraph.bullet).length;
      richRunCount += (object.paragraphs || []).reduce((count, paragraph) => count + Math.max(0, (paragraph.runs || []).length - 1), 0);
    }
  }
  return { paragraph_count: paragraphCount, bullet_paragraph_count: bulletCount, additional_rich_runs: richRunCount };
}

function summarizeTransforms() {
  const transforms = [];
  for (const slide of app.deck.slides) {
    for (const object of slide.objects) {
      if (object.type === "shape" || object.type === "image") {
        transforms.push({
          slide_id: slide.id,
          object_id: object.id,
          object_type: object.type,
          rotation: object.rotation || 0,
          flipX: Boolean(object.flipX),
          flipY: Boolean(object.flipY),
          radius: object.radius ?? null,
          safeRef: object.type === "image" ? object.safeRef : null,
        });
      }
    }
  }
  return transforms.slice(0, 40);
}

function markSaved(text) {
  refs.saveStatus.textContent = text || UI_TEXT[app.locale].labels.saved;
  window.clearTimeout(markSaved.timer);
  markSaved.timer = window.setTimeout(() => {
    refs.saveStatus.textContent = UI_TEXT[app.locale].labels.saved;
  }, 900);
}

function setMode(mode) {
  if (!app.data.product_boundary.modes.includes(mode)) return;
  app.mode = mode;
  $$(".mode-switch button").forEach((button) => {
    button.setAttribute("aria-selected", String(button.dataset.mode === mode));
  });
  refs.modeNote.textContent = mode === "assistant" ? UI_TEXT[app.locale].mode.assistantNote : UI_TEXT[app.locale].mode.autoNote;
}

function openFeatureSurface(surface) {
  const titles = UI_TEXT[app.locale].surfaces;
  if (!titles[surface]) return;
  refs.featureSurface.hidden = false;
  refs.featureSurface.dataset.activeSurface = surface;
  refs.featureSurfaceTitle.textContent = titles[surface];
  updateFeatureSurfaceOffset();
  $$("[data-surface]").forEach((button) => button.classList.toggle("is-active", button.dataset.surface === surface));
  $$("[data-feature-panel]").forEach((panel) => {
    panel.hidden = panel.dataset.featurePanel !== surface;
  });
  requestAnimationFrame(() => {
    refs.featureSurface.querySelector('[data-action="close-surface"]')?.focus();
  });
}

function closeFeatureSurface() {
  const activeSurface = refs.featureSurface.dataset.activeSurface;
  refs.featureSurface.hidden = true;
  delete refs.featureSurface.dataset.activeSurface;
  $$("[data-surface]").forEach((button) => button.classList.remove("is-active"));
  if (activeSurface) {
    document.querySelector(`[data-surface="${CSS.escape(activeSurface)}"]`)?.focus();
  }
}

function updateFeatureSurfaceOffset() {
  const toolbarBottom = $(".toolbar")?.getBoundingClientRect().bottom || 104;
  document.documentElement.style.setProperty("--feature-surface-top", `${Math.ceil(toolbarBottom + 12)}px`);
}

function updateCanvasScale() {
  const frameRect = refs.canvasFrame.getBoundingClientRect();
  const availableWidth = Math.max(320, frameRect.width - 24);
  const availableHeight = Math.max(240, frameRect.height - 24);
  const fitScale = Math.min(availableWidth / CANVAS_WIDTH, availableHeight / CANVAS_HEIGHT, 1);
  const scale = app.zoomMode === "fit" ? fitScale : clamp(app.manualZoom, 0.28, 1.4);
  app.scale = scale;
  refs.canvasViewport.style.setProperty("--canvas-scale", String(scale));
  refs.canvas.style.setProperty("--canvas-scale", String(scale));
  refs.canvasViewport.style.width = `${Math.ceil(CANVAS_WIDTH * scale)}px`;
  refs.canvasViewport.style.height = `${Math.ceil(CANVAS_HEIGHT * scale)}px`;
  refs.zoomLabel.textContent = app.zoomMode === "fit"
    ? `${app.locale === "ko" ? "맞춤" : "Fit"} ${Math.round(scale * 100)}%`
    : `${Math.round(scale * 100)}%`;
}

function styleObject(el, object) {
  el.style.left = `${object.x}px`;
  el.style.top = `${object.y}px`;
  el.style.width = `${object.w}px`;
  el.style.height = `${object.h}px`;
  el.style.zIndex = String(object.z || 1);
  el.dataset.objectId = object.id;
  el.dataset.objectType = object.type;
  if (object.fill) el.style.background = object.fill;
  if (object.stroke) el.style.borderColor = object.stroke;
  if (object.radius !== undefined) el.style.borderRadius = `${object.radius}px`;
  const flipX = object.flipX ? -1 : 1;
  const flipY = object.flipY ? -1 : 1;
  el.style.transform = `rotate(${object.rotation || 0}deg) scale(${flipX}, ${flipY})`;
}

function renderTextObject(object) {
  const el = document.createElement("div");
  el.className = "slide-object slide-text";
  styleObject(el, object);
  el.style.color = object.color || "#151515";
  el.style.fontSize = `${object.fontSize || 24}px`;
  el.style.fontWeight = String(object.fontWeight || 500);
  el.style.lineHeight = String(object.lineHeight || 1.2);
  el.dataset.textRole = object.textRole || "Body";
  el.dataset.textRotationDisabled = "true";
  for (const paragraph of object.paragraphs || textToParagraphs(object.text || "", object)) {
    const paragraphEl = document.createElement("div");
    paragraphEl.className = "text-paragraph";
    paragraphEl.dataset.role = paragraph.role || object.textRole || "Body";
    paragraphEl.dataset.bullet = String(Boolean(paragraph.bullet));
    const prefix = paragraph.bullet ? `${"  ".repeat(paragraph.bulletLevel || 0)}• ` : "";
    if (prefix) paragraphEl.append(document.createTextNode(prefix));
    for (const run of paragraph.runs || []) {
      const span = document.createElement("span");
      span.textContent = run.text || "";
      span.dataset.richTextRun = "true";
      if (run.color) span.style.color = run.color;
      if (run.fontSize) span.style.fontSize = `${run.fontSize}px`;
      if (run.fontWeight) span.style.fontWeight = String(run.fontWeight);
      if (run.italic) span.style.fontStyle = "italic";
      if (run.underline) span.style.textDecoration = "underline";
      paragraphEl.append(span);
    }
    el.append(paragraphEl);
  }
  if (object.fill) {
    el.style.background = object.fill;
    el.style.justifyContent = "center";
    el.style.textAlign = "center";
  }
  if (object.radius !== undefined) {
    el.style.borderRadius = `${object.radius}px`;
  }
  el.addEventListener("dblclick", (event) => {
    event.stopPropagation();
    beginInlineTextEdit(object.id);
  });
  el.addEventListener("paste", handlePlainTextPaste);
  return el;
}

function renderShapeObject(object) {
  const el = document.createElement("div");
  el.className = "slide-object slide-shape";
  styleObject(el, object);
  el.style.background = object.fill || "transparent";
  el.style.border = `2px solid ${object.stroke || "transparent"}`;
  return el;
}

function renderLineObject(object) {
  const el = document.createElement("div");
  el.className = "slide-object slide-line";
  styleObject(el, object);
  el.style.borderTop = `${object.strokeWidth || 2}px solid ${object.stroke || "#151515"}`;
  return el;
}

function renderImageObject(object) {
  const el = document.createElement("div");
  el.className = "slide-object slide-image";
  styleObject(el, object);
  el.style.backgroundColor = object.fill || "#e8ecea";
  const label = document.createElement("span");
  label.className = "slide-image-label";
  label.textContent = object.label || object.safeRef || "safe asset slot";
  el.append(label);
  return el;
}

function renderTableObject(object) {
  const wrapper = document.createElement("div");
  wrapper.className = "slide-object slide-table";
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
  let el;
  if (object.type === "text") el = renderTextObject(object);
  else if (object.type === "shape") el = renderShapeObject(object);
  else if (object.type === "image") el = renderImageObject(object);
  else if (object.type === "table") el = renderTableObject(object);
  else if (object.type === "line") el = renderLineObject(object);
  else el = renderShapeObject(object);

  el.addEventListener("pointerdown", (event) => {
    if (app.editingObjectId) return;
    selectObject(object.id, event.shiftKey);
    startObjectDrag(event, object.id);
  });
  if (app.selectedObjectIds.includes(object.id)) {
    el.classList.add("is-selected");
    if (app.selectedObjectIds.length > 1) el.classList.add("is-multi-selected");
    addResizeHandles(el, object.id);
  }
  return el;
}

function addResizeHandles(el, objectId) {
  for (const handle of ["nw", "ne", "sw", "se"]) {
    const node = document.createElement("span");
    node.className = "resize-handle";
    node.dataset.handle = handle;
    node.addEventListener("pointerdown", (event) => {
      event.stopPropagation();
      startResize(event, objectId, handle);
    });
    el.append(node);
  }
}

function renderCanvas() {
  if (app.editingObjectId) {
    const objectId = app.editingObjectId;
    const editingEl = refs.canvas.querySelector(`[data-object-id="${CSS.escape(objectId)}"]`);
    const editingObject = activeSlide().objects.find((item) => item.id === objectId);
    if (editingEl) {
      editingEl.removeEventListener("input", onInlineTextInput);
      editingEl.removeEventListener("mouseup", captureActiveTextSelection);
      editingEl.removeEventListener("keyup", captureActiveTextSelection);
      if (app.inlineEditBlurHandler) editingEl.removeEventListener("blur", app.inlineEditBlurHandler);
      if (app.inlineEditKeyHandler) editingEl.removeEventListener("keydown", app.inlineEditKeyHandler);
      if (editingObject) setObjectText(editingObject, editingEl.textContent || "");
    }
    app.editingObjectId = null;
    app.inlineEditBlurHandler = null;
    app.inlineEditKeyHandler = null;
  }
  const slide = activeSlide();
  refs.slideTitle.textContent = slide.title;
  refs.canvas.style.background = slide.background || "#ffffff";
  refs.canvas.replaceChildren();
  const sorted = [...slide.objects].sort((a, b) => (a.z || 0) - (b.z || 0));
  for (const object of sorted) refs.canvas.append(renderObject(object));
  updateInspector();
}

function renderSlideList() {
  refs.slideCount.textContent = `${app.deck.slides.length}`;
  refs.slideList.replaceChildren();
  app.deck.slides.forEach((slide, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `slide-thumb${index === app.activeSlideIndex ? " is-active" : ""}`;
    button.dataset.slideId = slide.id;
    const preview = document.createElement("div");
    preview.className = "thumb-preview";
    preview.style.background = slide.background || "#ffffff";
    for (const object of slide.objects.filter((item) => item.type !== "line").slice(0, 7)) {
      const thumb = document.createElement("span");
      thumb.className = "thumb-object";
      thumb.style.left = `${(object.x / CANVAS_WIDTH) * 100}%`;
      thumb.style.top = `${(object.y / CANVAS_HEIGHT) * 100}%`;
      thumb.style.width = `${(object.w / CANVAS_WIDTH) * 100}%`;
      thumb.style.height = `${(object.h / CANVAS_HEIGHT) * 100}%`;
      thumb.style.background = object.fill || (object.type === "image" ? "#dfe8e5" : "#132326");
      thumb.style.zIndex = String(object.z || 1);
      preview.append(thumb);
    }
    const title = document.createElement("span");
    title.className = "thumb-title";
    title.textContent = `${String(index + 1).padStart(2, "0")} ${slide.title}`;
    const section = document.createElement("span");
    section.className = "thumb-section";
    section.textContent = slide.section;
    button.append(preview, title, section);
    button.addEventListener("click", () => {
      app.activeSlideIndex = index;
      setSelection([]);
      renderAll();
      recordOperation("navigate_slide", { summary: `selected slide ${index + 1}` });
    });
    refs.slideList.append(button);
  });
}

function countSafeAssetRefs() {
  const explicitRefs = app.data.safe_asset_refs || [];
  const objectRefs = app.deck.slides.flatMap((slide) => slide.objects || [])
    .filter((object) => object.safeRef)
    .map((object) => object.safeRef);
  return new Set([
    ...explicitRefs.map((item) => item.safe_asset_ref || item.safeRef || ""),
    ...objectRefs,
  ].filter(Boolean)).size;
}

function renderWorkStateSummary() {
  if (!refs.workStateSummary || !app.data || !app.deck) return;
  const fixture = app.data.fixture_metadata?.is_fixture === true;
  const designPackage = app.data.design_package?.design_package_id || "design package pending";
  const sourceStatus = app.data.design_package?.source_status || app.data.asset_system_consumption?.status || "local preview";
  const theme = app.data.theme_tokens?.theme_id || "theme pending";
  const revisionCount = app.revisionMemory?.length || 0;
  const exportState = app.data.export_hooks?.current_status || "handoff_ready";
  const safeRefs = countSafeAssetRefs();
  refs.workStateSummary.textContent = app.locale === "ko"
    ? `${fixture ? "샘플 작업" : "생성 작업"} · 디자인 ${localizedValue(sourceStatus)} · 테마 ${theme} · 수정 ${revisionCount} · 내보내기 ${localizedValue(exportState)} · 안전 에셋 ${safeRefs}`
    : `${fixture ? "Sample work" : "Generated work"} · design ${localizedValue(sourceStatus)} · theme ${theme} · revisions ${revisionCount} · export ${localizedValue(exportState)} · safe assets ${safeRefs}`;
  refs.workStateSummary.dataset.fixture = String(fixture);
}

function renderAll() {
  refs.deckLabel.textContent = app.deck.safe_label;
  renderWorkStateSummary();
  renderSlideList();
  renderCanvas();
  updateCanvasScale();
  renderStyleSummary();
  renderRevisionMemory();
  renderCommercialScaffolds();
  renderDiagnostics();
}

function selectObject(id, additive = false) {
  const before = app.selectedObjectIds.join("|");
  if (additive) {
    const next = app.selectedObjectIds.includes(id)
      ? app.selectedObjectIds.filter((item) => item !== id)
      : [...app.selectedObjectIds, id];
    setSelection(next);
  } else {
    setSelection([id]);
  }
  if (before !== app.selectedObjectIds.join("|")) {
    renderCanvas();
  } else {
    updateInspector();
  }
}

function showCommandFeedback(message) {
  if (!refs.commandFeedback) return;
  refs.commandFeedback.textContent = message;
  refs.commandFeedback.classList.remove("is-visible");
  window.clearTimeout(app.feedbackTimer);
  requestAnimationFrame(() => refs.commandFeedback.classList.add("is-visible"));
  app.feedbackTimer = window.setTimeout(() => {
    refs.commandFeedback.textContent = "";
    refs.commandFeedback.classList.remove("is-visible");
  }, 1800);
}

function setToolbarDisabled(actions, disabled) {
  for (const action of actions) {
    document.querySelector(`[data-action="${action}"]`)?.toggleAttribute("disabled", disabled);
  }
}

function updateToolbarState() {
  const objects = selectedObjects();
  const single = objects.length === 1 ? objects[0] : null;
  const hasSelection = objects.length > 0;
  const hasText = objects.some((object) => object.type === "text");
  const hasShapeImage = objects.some((object) => object.type === "shape" || object.type === "image");
  const hasShape = objects.some((object) => object.type === "shape");

  setToolbarDisabled(["duplicate-object", "delete-object", "bring-forward", "send-backward"], !hasSelection);
  setToolbarDisabled(["align-left", "align-center", "align-right", "align-top", "align-middle", "align-bottom"], !hasSelection);
  setToolbarDisabled(["distribute-horizontal", "distribute-vertical"], objects.length < 3);
  setToolbarDisabled(["rotate-minus-15", "rotate-plus-15", "rotate-minus-90", "rotate-plus-90", "rotate-reset", "flip-horizontal", "flip-vertical"], !hasShapeImage);
  setToolbarDisabled(["text-bold", "text-bullet", "align-text-left", "align-text-center", "align-text-right"], !single || single.type !== "text");
  refs.textRole.disabled = !single || single.type !== "text";
  refs.textFont.disabled = !single || single.type !== "text";
  refs.textSize.disabled = !single || single.type !== "text";
  refs.textColor.disabled = !single || single.type !== "text";
  refs.shapeRadius.disabled = !hasShape;
}

function updateInspector() {
  const objects = selectedObjects();
  const object = objects.length === 1 ? objects[0] : null;
  const bounds = objects.length > 1 ? selectionBounds(objects) : null;
  const state = objects.length === 0
    ? "none"
    : objects.length > 1
      ? "multi"
      : object.type;
  const labels = UI_TEXT[app.locale].labels;
  refs.inspector.dataset.inspectorState = state;
  refs.selectedLabel.textContent = objects.length > 1
    ? `${objects.length}${app.locale === "ko" ? labels.selectedCount : ` ${labels.selectedCount}`}`
    : object
      ? `${object.type} ${object.id}`
      : labels.noSelection;
  refs.inspectorState.textContent =
    state === "none"
      ? labels.selectObject
      : state === "multi"
        ? labels.multiSelection
        : state === "text"
          ? labels.textSelection
          : state === "shape"
            ? labels.shapeSelection
            : state === "image"
              ? labels.imageSelection
              : state === "table"
                ? labels.tableSelection
                : labels.lineSelection;
  for (const key of ["x", "y", "w", "h"]) {
    refs.geometry[key].disabled = !object;
    refs.geometry[key].value = object
      ? Math.round(object[key])
      : bounds
        ? Math.round(key === "x" ? bounds.x : key === "y" ? bounds.y : key === "w" ? bounds.right - bounds.x : bounds.bottom - bounds.y)
        : "";
  }
  refs.textEditor.disabled = !object || object.type !== "text";
  refs.textEditor.value = object?.type === "text" ? plainText(object) : "";
  if (object?.type === "text") {
    refs.textRole.value = object.textRole || "Body";
    refs.textFont.value = object.fontFamilyToken || "body";
    refs.textSize.value = object.fontSize || 24;
    refs.textColor.value = object.color || "#151515";
  }
  if (object) refs.shapeRadius.value = object.radius ?? 0;
  renderObjectStyleSummary(object, objects);
  updateToolbarState();
}

function renderDiagnostics() {
  refs.operationLog.textContent = JSON.stringify(sanitizedOperationSummary(), null, 2);
  refs.handoffEnvelope.textContent = app.activeExportEnvelope ? JSON.stringify(app.activeExportEnvelope, null, 2) : "";
}

function renderStyleSummary() {
  refs.styleSummary.replaceChildren();
  const masterSurface = ensureMasterSurface();
  syncMasterControls();
  const paletteName = MASTER_STYLE_PRESETS[masterSurface.selected_palette_id]?.[app.locale === "ko" ? "koLabel" : "label"] || masterSurface.selected_palette_id;
  const scaleName = TYPE_SCALE_PRESETS[masterSurface.type_scale_id]?.[app.locale === "ko" ? "koLabel" : "label"] || masterSurface.type_scale_id;
  const diff = masterSurface.preview_diff || {};
  const labels = app.locale === "ko"
    ? ["디자인 패키지", "테마", "마스터", "상태", "팔레트", "타이포그래피", "도형 반경", "미리보기 변경", "역할"]
    : ["Design package", "Theme", "Master", "State", "Palette", "Typography", "Shape radius", "Preview diff", "Roles"];
  const rows = [
    [labels[0], app.data.design_package.design_package_id],
    [labels[1], app.data.theme_tokens.theme_id],
    [labels[2], app.data.master_styles?.[0]?.master_style_id],
    [labels[3], `${masterSurface.active_style_id || "baseline"} / ${masterSurface.locked ? "locked" : "editable"}`],
    [labels[4], paletteName],
    [labels[5], scaleName],
    [labels[6], `${masterSurface.shape_radius}px`],
    [labels[7], `palette=${Boolean(diff.palette_changed)} type=${Boolean(diff.typography_changed)} shape=${Boolean(diff.shape_defaults_changed)} overrides=${diff.selected_overrides || 0}`],
    [labels[8], Object.keys(app.data.text_style_roles || {}).join(", ")],
  ];
  for (const [label, value] of rows) {
    const row = document.createElement("div");
    row.className = "style-row";
    row.textContent = `${label}: ${value}`;
    refs.styleSummary.append(row);
  }
}

function renderRevisionMemory() {
  refs.revisionMemory.replaceChildren();
  for (const memory of app.revisionMemory.slice(-5)) {
    const row = document.createElement("div");
    row.className = "memory-row";
    row.textContent = `${localizedValue(memory.kind)} / ${localizedValue(memory.mode)}: ${localizedValue(memory.summary)}`;
    refs.revisionMemory.append(row);
  }
}

function renderKeyValueList(container, rows) {
  if (!container) return;
  container.replaceChildren();
  for (const [label, value] of rows) {
    const row = document.createElement("div");
    row.className = "style-row";
    row.textContent = `${label}: ${localizedValue(value)}`;
    container.append(row);
  }
}

function localizedValue(value) {
  const maps = {
    ko: {
      none: "없음",
      ready: "준비됨",
      blocked: "차단됨",
      visible: "표시",
      hidden: "숨김",
      yes: "예",
      no: "아니요",
      read_only: "읽기 전용",
      "read-only": "읽기 전용",
      editable: "편집 가능",
      deleted: "삭제됨",
      user_visible: "사용자 표시",
      medium: "보통",
      high: "높음",
      low: "낮음",
      unset: "설정 안 됨",
      fixture_loaded: "샘플 작업 불러옴",
      assistant: "Assistant",
      auto: "Auto",
      "Public-safe fixture loaded for local workbench editing.": "내부 테스트용 샘플 작업을 불러왔습니다.",
      standard: "표준",
      baseline: "기본",
      local_contract_ready: "로컬 준비",
      safe_loader_ready: "안전 로더 준비",
      handoff_ready: "핸드오프 준비",
      handoff_sent: "핸드오프 전송됨",
      awaiting_host_ai: "Host AI 대기 중",
      proposal_ready: "제안 도착",
      final_missing: "최종 결과 없음",
      content_free_recipes_ready: "디자인 레시피 준비됨",
      local_host_ai_design_analysis_only: "로컬 디자인 분석만",
      content_free_metric_importer_ready: "디자인 레시피 가져오기 준비",
      asset_system_ready_without_package_consumption: "에셋 시스템 준비, 실제 패키지 미연결",
      asset_system_ready_no_approved_package_evidence: "에셋 시스템 준비, 실제 디자인 패키지 미연결",
      "asset-system-ready": "에셋 시스템 준비",
      safe_reference_ready: "안전한 에셋 참조 준비",
      scaffold_ready: "연결 준비",
      safe_ref_slot_only: "안전한 이미지 슬롯만",
      safe_ref_placeholder_only: "이미지 자리 표시만",
      large_safe_ref_slot_with_crop_policy: "큰 이미지 슬롯과 자르기 정책",
      editable_native_chart_table_guidance: "편집 가능한 차트/표 가이드",
      clean_metric_cards_without_source_data: "깔끔한 지표 카드",
      pending_connection: "연결 대기",
      made_with_attribution: "제작 표시",
      watermark_free: "워터마크 없음",
    },
    en: {
      none: "None",
      ready: "Ready",
      blocked: "Blocked",
      visible: "Visible",
      hidden: "Hidden",
      read_only: "Read-only",
      "read-only": "Read-only",
      editable: "Editable",
      deleted: "Deleted",
      user_visible: "User visible",
      medium: "Medium",
      high: "High",
      low: "Low",
      unset: "Not set",
      fixture_loaded: "Sample work loaded",
      assistant: "Assistant",
      auto: "Auto",
      "Public-safe fixture loaded for local workbench editing.": "Sample work loaded for internal testing.",
      standard: "Standard",
      baseline: "Baseline",
      local_contract_ready: "Local preview ready",
      safe_loader_ready: "Safe loader ready",
      handoff_ready: "Handoff ready",
      handoff_sent: "Handoff sent",
      awaiting_host_ai: "Awaiting host AI",
      proposal_ready: "Proposal ready",
      final_missing: "No final result",
      content_free_recipes_ready: "Design recipes ready",
      local_host_ai_design_analysis_only: "Local design analysis only",
      content_free_metric_importer_ready: "Design recipe importer ready",
      asset_system_ready_without_package_consumption: "Asset system ready; no real package connected",
      asset_system_ready_no_approved_package_evidence: "Asset system ready; no real design package connected",
      "asset-system-ready": "Asset-system ready",
      safe_reference_ready: "Safe asset references ready",
      scaffold_ready: "Connection ready",
      safe_ref_slot_only: "Safe image slot only",
      safe_ref_placeholder_only: "Image placeholder only",
      large_safe_ref_slot_with_crop_policy: "Large image slot with crop policy",
      editable_native_chart_table_guidance: "Editable chart/table guidance",
      clean_metric_cards_without_source_data: "Clean metric cards",
      pending_connection: "Pending connection",
      made_with_attribution: "Attribution shown",
      watermark_free: "Watermark-free",
    },
  };
  if (typeof value === "boolean") return app.locale === "ko" ? (value ? "예" : "아니요") : (value ? "Yes" : "No");
  if (Array.isArray(value)) return value.map(localizedValue).join(", ");
  const map = maps[app.locale] || maps.en;
  return map[String(value)] || value;
}

function renderObjectStyleSummary(object, objects = []) {
  if (!refs.objectStyleSummary) return;
  const labels = app.locale === "ko"
    ? {
      style: "스타일",
      selectObject: "오브젝트를 선택하세요",
      selection: "선택",
      objects: "개 오브젝트",
      editScope: "편집 범위",
      sharedGeometry: "공통 위치/크기만",
      role: "역할",
      theme: "테마",
      layout: "레이아웃",
      component: "컴포넌트",
      transform: "변환",
      degree: "도",
      flip: "뒤집기",
      assetRef: "에셋 참조",
      safeSlot: "안전 슬롯",
    }
    : {
      style: "Style",
      selectObject: "Select an object",
      selection: "Selection",
      objects: "objects",
      editScope: "Edit scope",
      sharedGeometry: "shared geometry only",
      role: "Role",
      theme: "Theme",
      layout: "Layout",
      component: "Component",
      transform: "Transform",
      degree: "deg",
      flip: "flip",
      assetRef: "Asset ref",
      safeSlot: "safe slot",
    };
  if (!object && objects.length <= 1) {
    renderKeyValueList(refs.objectStyleSummary, [[labels.style, labels.selectObject]]);
    return;
  }
  if (!object && objects.length > 1) {
    renderKeyValueList(refs.objectStyleSummary, [
      [labels.selection, app.locale === "ko" ? `${objects.length}${labels.objects}` : `${objects.length} ${labels.objects}`],
      [labels.editScope, labels.sharedGeometry],
    ]);
    return;
  }
  const slide = activeSlide();
  const rows = [
    [labels.role, object.type === "text" ? object.textRole || "Body" : object.type],
    [labels.theme, slide.theme_id || app.data.theme_tokens?.theme_id],
    [labels.layout, slide.layout_recipe_id || "none"],
    [labels.component, slide.component_recipe_id || "none"],
  ];
  if (object.type === "shape" || object.type === "image") {
    rows.push([labels.transform, `${object.rotation || 0} ${labels.degree} / ${labels.flip} ${object.flipX ? "H" : "-"}${object.flipY ? "V" : "-"}`]);
  }
  if (object.type === "image") rows.push([labels.assetRef, object.safeRef || labels.safeSlot]);
  renderKeyValueList(refs.objectStyleSummary, rows);
}

function ensureMasterSurface() {
  const surface = app.data.master_style_surface ||= {};
  surface.active_style_id ||= app.data.master_styles?.[0]?.master_style_id || "master-style-commercial-mvp-v1";
  surface.selected_palette_id ||= "baseline";
  surface.type_scale_id ||= "standard";
  surface.shape_radius ??= app.data.master_styles?.[0]?.shape_defaults?.radius || app.data.theme_tokens?.radius?.card || 8;
  surface.preview_diff ||= { palette_changed: false, typography_changed: false, shape_defaults_changed: false, selected_overrides: 0 };
  return surface;
}

function syncMasterControls() {
  const surface = ensureMasterSurface();
  if (refs.masterPalette) refs.masterPalette.value = surface.selected_palette_id;
  if (refs.masterTypeScale) refs.masterTypeScale.value = surface.type_scale_id;
  if (refs.masterRadius) refs.masterRadius.value = String(surface.shape_radius);
  updateMasterPreview();
}

function selectedMasterSettings() {
  const surface = ensureMasterSurface();
  return {
    paletteId: refs.masterPalette?.value || surface.selected_palette_id,
    typeScaleId: refs.masterTypeScale?.value || surface.type_scale_id,
    radius: Number(refs.masterRadius?.value || surface.shape_radius || 8),
  };
}

function applyThemeSettings(settings) {
  const palette = MASTER_STYLE_PRESETS[settings.paletteId]?.palette || MASTER_STYLE_PRESETS.baseline.palette;
  const scale = TYPE_SCALE_PRESETS[settings.typeScaleId]?.multiplier || 1;
  const baselineRoles = app.baselineStyleData?.text_style_roles || app.data.text_style_roles || {};
  app.data.theme_tokens.palette = clone(palette);
  app.data.theme_tokens.theme_id = `theme-adreammaker-${settings.paletteId}-v1`;
  app.data.theme_tokens.radius ||= {};
  app.data.theme_tokens.radius.card = settings.radius;
  app.data.theme_tokens.stroke ||= {};
  app.data.theme_tokens.stroke.default = palette.muted;
  app.data.text_style_roles = {};
  for (const [role, roleData] of Object.entries(baselineRoles)) {
    app.data.text_style_roles[role] = {
      ...clone(roleData),
      fontSize: Math.round((roleData.fontSize || 24) * scale),
      color: role === "Body" || role === "Caption" ? palette.muted : palette.ink,
    };
  }
  const master = app.data.master_styles?.[0];
  if (master) {
    master.theme_id = app.data.theme_tokens.theme_id;
    master.shape_defaults = { radius: settings.radius, stroke: palette.muted };
  }
}

function applyThemeToDeckObjects() {
  const palette = app.data.theme_tokens.palette || MASTER_STYLE_PRESETS.baseline.palette;
  const masterDefaults = app.data.master_styles?.[0]?.shape_defaults || {};
  for (const slide of app.deck.slides) {
    slide.master_style_id = ensureMasterSurface().active_style_id;
    slide.theme_id = app.data.theme_tokens.theme_id;
    slide.token_set_id = app.data.theme_tokens.token_set_id;
    if (slide.background === "#FFFFFF" || slide.background === "#F7F5EF" || slide.background === "#F4F7F2" || slide.background === "#EEF2F3") {
      slide.background = slide.section === "Opening" ? palette.surface : palette.canvas;
    }
    for (const object of slide.objects) {
      if (object.type === "text") {
        const role = object.textRole || inferTextRole(object);
        const roleDefaults = app.data.text_style_roles?.[role] || {};
        object.fontSize = roleDefaults.fontSize || object.fontSize;
        object.fontWeight = roleDefaults.fontWeight || object.fontWeight;
        object.color = roleDefaults.color || object.color;
        object.lineHeight = roleDefaults.lineHeight || object.lineHeight;
        object.paragraphs = textToParagraphs(plainText(object), object);
      }
      if (object.type === "shape") {
        object.radius = masterDefaults.radius ?? object.radius;
        if (object.stroke && object.stroke !== "transparent") object.stroke = masterDefaults.stroke || object.stroke;
      }
    }
  }
}

function updateMasterPreview() {
  const preview = $(".master-preview");
  if (!preview || !app.data?.theme_tokens) return;
  const palette = app.data.theme_tokens.palette || MASTER_STYLE_PRESETS.baseline.palette;
  preview.style.background = `linear-gradient(90deg, ${palette.surface} 0 68%, ${palette.deep} 68% 100%)`;
  $(".preview-title-line")?.style.setProperty("background", palette.ink);
  $(".preview-body-line")?.style.setProperty("background", palette.muted);
  $(".preview-chip-line")?.style.setProperty("background", palette.accent);
}

function styleMemoryProfile() {
  return app.data.style_memory_profiles?.[0] || null;
}

function recipeIsContentFree(recipe) {
  return recipe?.content_free_preview?.placeholder_labels_only === true
    || recipe?.synthetic_placeholder_preview?.placeholder_labels_only === true;
}

function referenceDesignHandoffSummary() {
  const library = app.data.reference_design_library || {};
  const recipes = library.recipes || [];
  return {
    library_id: library.library_id || null,
    recipe_count: recipes.length,
    extraction_source: library.extraction_source || null,
    content_free_only: recipes.length > 0 && recipes.every(recipeIsContentFree),
    content_free_schema_support: {
      content_free_preview_placeholder_labels_only: true,
      synthetic_placeholder_preview_placeholder_labels_only: true,
    },
    server_stores_original_files: library.server_storage_policy?.stores_original_files === true,
  };
}

function styleMemoryHandoffSummary() {
  const profile = styleMemoryProfile();
  if (!profile) return { profile_id: null, visible: false, preference_count: 0 };
  return {
    profile_id: profile.profile_id,
    visible: profile.visibility === "user_visible",
    controls: profile.user_controls,
    separate_from_undo_redo: profile.separate_from_undo_redo,
    separate_from_ai_revision_memory: profile.separate_from_ai_revision_memory,
    preference_count: profile.public_handoff_summary?.preference_count || 0,
    content_free: profile.public_handoff_summary?.content_free === true,
  };
}

function publishedViewHandoffSummary() {
  return (app.data.published_views || []).map((view) => ({
    view_id: view.view_id,
    route: view.route,
    plan: view.plan,
    read_only: view.read_only,
    watermark: view.watermark,
  }));
}

function referralCreditHandoffSummary() {
  const referral = app.data.referral_entitlement || {};
  return {
    public_plans: referral.plan_model?.public_plans || [],
    paid_visible_per_edit_credit: referral.plan_model?.paid_visible_per_edit_credit === true,
    activation_event_count: referral.activation_events?.length || 0,
    free_credit_ledger_count: referral.free_credit_ledger?.length || 0,
    paid_fair_use_ref: referral.paid_fair_use_entitlement?.entitlement_ref || null,
  };
}

function safeAssetDesignRefs() {
  return {
    design_package_id: app.data.design_package?.design_package_id || null,
    theme_id: app.data.theme_tokens?.theme_id || null,
    master_style_id: app.data.master_styles?.[0]?.master_style_id || null,
    layout_recipe_ids: (app.data.layout_recipes || []).map((recipe) => recipe.layout_recipe_id),
    component_recipe_ids: (app.data.component_recipes || []).map((recipe) => recipe.component_recipe_id),
    reference_recipe_ids: (app.data.reference_design_library?.recipes || []).map((recipe) => recipe.recipe_id),
  };
}

function renderCommercialScaffolds() {
  const library = app.data.reference_design_library || {};
  const profile = styleMemoryProfile();
  const freeView = (app.data.published_views || []).find((view) => view.plan === "free") || {};
  const paidView = (app.data.published_views || []).find((view) => view.plan === "paid") || {};
  const referral = app.data.referral_entitlement || {};
  const localAssets = app.data.local_asset_connection_ux || {};
  const labels = app.locale === "ko"
    ? {
      library: "라이브러리", recipes: "레시피", importer: "가져오기", families: "군", extraction: "추출", filesStored: "파일 저장",
      profile: "프로필", controls: "제어", density: "밀도", status: "상태", free: "무료", paid: "유료", route: "경로",
      plans: "플랜", rewards: "활성 보상", ledger: "무료 장부", paidMeter: "유료 편집 미터", package: "패키지", claim: "표기", fonts: "글꼴", images: "이미지", rawImage: "원본 이미지 저장"
    }
    : {
      library: "Library", recipes: "Recipes", importer: "Importer", families: "Families", extraction: "Extraction", filesStored: "Files stored",
      profile: "Profile", controls: "Controls", density: "Density", status: "Status", free: "Free", paid: "Paid", route: "Route",
      plans: "Plans", rewards: "Activation rewards", ledger: "Free ledger", paidMeter: "Paid edits meter", package: "Package", claim: "Claim", fonts: "Fonts", images: "Images", rawImage: "Stores raw image"
    };
  renderReferenceLibrary(library, labels);
  renderKeyValueList(refs.styleMemory, profile ? [
    [labels.profile, profile.profile_id],
    [labels.controls, profile.user_controls.join(", ")],
    [labels.density, profile.preferences.density_preference],
    [labels.status, profile.visibility],
  ] : [[labels.profile, "deleted"]]);
  renderKeyValueList(refs.publishedView, [
    [labels.free, `${localizedValue(freeView.watermark || "none")} / ${localizedValue(freeView.read_only ? "read-only" : "editable")}`],
    [labels.paid, `${localizedValue(paidView.watermark || "none")} / ${localizedValue(paidView.read_only ? "read-only" : "editable")}`],
    [labels.route, freeView.route || "viewer.html"],
  ]);
  renderKeyValueList(refs.referralCredit, [
    [labels.plans, (referral.plan_model?.public_plans || []).join(" + ")],
    [labels.rewards, referral.activation_events?.filter((event) => event.reward_eligible).length || 0],
    [labels.ledger, referral.free_credit_ledger?.length || 0],
    [labels.paidMeter, referral.plan_model?.paid_visible_per_edit_credit ? "visible" : "hidden"],
  ]);
  renderKeyValueList(refs.localAssets, [
    [labels.package, app.data.asset_system_consumption?.status || app.data.design_package?.source_status || "ready"],
    [labels.claim, app.data.asset_system_consumption?.ui_claim || "asset-system-ready"],
    [labels.fonts, localAssets.font_connection?.status || "pending"],
    [labels.images, localAssets.image_connection?.status || "pending"],
    [labels.rawImage, localAssets.image_connection?.stores_original_image ? "yes" : "no"],
  ]);
}

function renderReferenceLibrary(library, labels) {
  if (!refs.referenceLibrary) return;
  refs.referenceLibrary.replaceChildren();
  const recipes = library.recipes || [];
  const aggregateRecipe = recipes[0] || {};
  const applyFlow = library.apply_flow || {};
  const familyIds = library.importer?.benchmark_family_ids || ["ir", "sales", "portfolio"];
  const summaryRows = [
    [labels.library, app.locale === "ko" ? "내용 제외 디자인 라이브러리" : "Content-free design library"],
    [labels.recipes, recipes.length || 0],
    [labels.importer, library.importer?.last_import_status || library.importer?.status || "ready"],
    [labels.extraction, library.extraction_source || "none"],
    [labels.filesStored, library.server_storage_policy?.stores_original_files ? "blocked" : "no"],
  ];
  for (const [label, value] of summaryRows) {
    const row = document.createElement("div");
    row.className = "style-row";
    row.textContent = `${label}: ${localizedValue(value)}`;
    refs.referenceLibrary.append(row);
  }
  if (refs.referenceApplySummary) {
    refs.referenceApplySummary.textContent = applyFlow.before_after_summary
      ? localizedValue(applyFlow.before_after_summary)
      : app.locale === "ko"
        ? "아직 이 세션에서 적용한 레시피가 없습니다. 적용해도 원본 내용은 포함되지 않습니다."
        : "No recipe has been applied in this session. Applying a recipe still excludes source content.";
  }
  const cardWrap = document.createElement("div");
  cardWrap.className = "recipe-card-grid";
  const recipeDensity = aggregateRecipe.density || aggregateRecipe.analysis_metrics?.object_density || "medium";
  const imageSlot = aggregateRecipe.image_slot_treatment || "safe_ref_placeholder_only";
  const chartTable = aggregateRecipe.chart_table_style || "clean_metric_cards_without_source_data";
  for (const familyId of familyIds) {
    const family = REFERENCE_FAMILY_CARDS[familyId] || { label: familyId, koLabel: familyId, tone: "Reusable design tone", koTone: "재사용 가능한 디자인 톤" };
    const card = document.createElement("article");
    card.className = "recipe-card";
    const title = document.createElement("h4");
    title.textContent = app.locale === "ko" ? `${family.koLabel} 레시피` : `${family.label} recipe`;
    const badge = document.createElement("span");
    badge.className = "recipe-badge";
    badge.textContent = app.locale === "ko" ? "내용 제외" : "Content-free";
    const head = document.createElement("div");
    head.className = "recipe-card-head";
    head.append(title, badge);
    const body = document.createElement("dl");
    body.className = "recipe-meta";
    const rows = app.locale === "ko"
      ? [
        ["밀도", localizedValue(recipeDensity)],
        ["이미지 슬롯", localizedValue(imageSlot)],
        ["차트/표", localizedValue(chartTable)],
        ["톤", family.koTone],
        ["적용 상태", localizedValue(library.importer?.last_import_status || "ready")],
      ]
      : [
        ["Density", localizedValue(recipeDensity)],
        ["Image slot", localizedValue(imageSlot)],
        ["Chart/table", localizedValue(chartTable)],
        ["Tone", family.tone],
        ["Apply status", localizedValue(library.importer?.last_import_status || "ready")],
      ];
    for (const [term, value] of rows) {
      const dt = document.createElement("dt");
      dt.textContent = term;
      const dd = document.createElement("dd");
      dd.textContent = value;
      body.append(dt, dd);
    }
    const actions = document.createElement("div");
    actions.className = "inline-actions";
    const apply = document.createElement("button");
    apply.type = "button";
    apply.dataset.action = "apply-reference-recipe";
    apply.dataset.family = familyId;
    apply.textContent = app.locale === "ko" ? "적용" : "Apply";
    actions.append(apply);
    card.append(head, body, actions);
    cardWrap.append(card);
  }
  refs.referenceLibrary.append(cardWrap);
}

function applyReferenceRecipe(familyId) {
  const library = app.data.reference_design_library || {};
  const recipe = (library.recipes || []).find((item) => item.family_id === familyId) || library.recipes?.[0];
  if (!recipe || !recipeIsContentFree(recipe)) {
    showCommandFeedback(app.locale === "ko" ? "내용 제외 레시피만 적용할 수 있습니다." : "Only content-free recipes can be applied.");
    return;
  }
  pushHistory(`apply reference recipe ${familyId}`);
  library.apply_flow = {
    last_applied_recipe_id: recipe.recipe_id,
    family_id: familyId,
    before_after_summary: app.locale === "ko"
      ? "적용 전: 현재 테마 유지. 적용 후: 팔레트, 타입 역할, 레이아웃/컴포넌트 참조만 업데이트. 원본 내용은 제외됨."
      : "Before: current theme kept. After: only palette, type-role, layout, and component references update. Source content remains excluded.",
    affected_tokens: ["palette", "typography", "layout_recipe", "component_recipe"],
    undo_available: true,
    reset_available: true,
    content_excluded: true,
  };
  const accent = app.data.theme_tokens?.palette?.accent;
  for (const slide of app.deck.slides) {
    slide.layout_recipe_id ||= recipe.layout_archetypes?.[0] || "content_free_recipe";
    slide.component_recipe_id ||= recipe.component_recipes?.[0] || "content_free_component";
    for (const object of slide.objects || []) {
      if (object.type === "shape" && object.fill !== "transparent" && accent) {
        object.stroke = accent;
      }
    }
  }
  recordOperation("reference_design_recipe_apply", { summary: `content-free recipe applied: ${recipe.recipe_id}` });
  renderAll();
  openFeatureSurface("design-library");
  showCommandFeedback(app.locale === "ko" ? "내용 없이 디자인 레시피만 적용했습니다." : "Applied the design recipe without source content.");
}

function resetReferenceRecipe() {
  const library = app.data.reference_design_library || {};
  if (!library.apply_flow?.last_applied_recipe_id) {
    showCommandFeedback(app.locale === "ko" ? "되돌릴 레시피 적용 내역이 없습니다." : "No applied recipe to reset.");
    return;
  }
  pushHistory("reset reference recipe");
  library.apply_flow = {
    before_after_summary: app.locale === "ko"
      ? "레시피 적용 상태를 기본값으로 되돌렸습니다. 원본 내용은 계속 제외됩니다."
      : "Recipe application reset to the default state. Source content remains excluded.",
    affected_tokens: [],
    undo_available: true,
    reset_available: false,
    content_excluded: true,
  };
  recordOperation("reference_design_recipe_reset", { summary: "content-free recipe application reset" });
  renderAll();
  openFeatureSurface("design-library");
}

function applyMasterStyle(action) {
  const surface = ensureMasterSurface();
  if (action === "lock") {
    surface.locked = !surface.locked;
    document.querySelector('[data-action="master-lock"]')?.setAttribute("aria-pressed", String(surface.locked));
    recordOperation("master_style_lock_toggle", { summary: surface.locked ? "deck master style locked" : "deck master style unlocked" });
    renderStyleSummary();
    showCommandFeedback(surface.locked
      ? (app.locale === "ko" ? "마스터 스타일을 잠갔습니다." : "Master Style locked.")
      : (app.locale === "ko" ? "마스터 스타일 잠금을 풀었습니다." : "Master Style unlocked."));
    return;
  }
  if (surface.locked && action !== "reset") {
    showCommandFeedback(app.locale === "ko" ? "마스터 스타일이 잠겨 있습니다." : "Master Style is locked.");
    return;
  }
  pushHistory(`master style ${action}`);
  if (action === "apply") {
    const settings = selectedMasterSettings();
    surface.selected_palette_id = settings.paletteId;
    surface.type_scale_id = settings.typeScaleId;
    surface.shape_radius = settings.radius;
    surface.preview_diff = {
      palette_changed: surface.selected_palette_id !== "baseline",
      typography_changed: surface.type_scale_id !== "standard",
      shape_defaults_changed: Number(surface.shape_radius) !== (app.baselineStyleData?.master_styles?.[0]?.shape_defaults?.radius || 8),
      selected_overrides: surface.preview_diff?.selected_overrides || 0,
    };
    applyThemeSettings(settings);
    applyThemeToDeckObjects();
  }
  if (action === "override") {
    const object = selectedObject();
    if (!object) {
      app.undoStack.pop();
      showCommandFeedback(app.locale === "ko" ? "오버라이드할 오브젝트를 선택하세요." : "Select an object to override.");
      return;
    }
    const settings = selectedMasterSettings();
    applyThemeSettings(settings);
    const palette = app.data.theme_tokens.palette || MASTER_STYLE_PRESETS.baseline.palette;
    if (object.type === "text") {
      const role = object.textRole || inferTextRole(object);
      const roleDefaults = app.data.text_style_roles?.[role] || {};
      object.fontSize = roleDefaults.fontSize || object.fontSize;
      object.fontWeight = roleDefaults.fontWeight || object.fontWeight;
      object.color = roleDefaults.color || object.color;
      object.lineHeight = roleDefaults.lineHeight || object.lineHeight;
      object.paragraphs = textToParagraphs(plainText(object), object);
    }
    if (object.type === "shape" || object.type === "image") {
      object.radius = settings.radius;
      object.stroke = object.type === "shape" ? palette.muted : object.stroke;
      object.fill = object.type === "shape" && object.fill !== "transparent" ? palette.surface : object.fill;
    }
    object.styleOverride = {
      source: "master_style_surface",
      palette_id: settings.paletteId,
      type_scale_id: settings.typeScaleId,
      shape_radius: settings.radius,
    };
    surface.override_count = (surface.override_count || 0) + 1;
    surface.preview_diff = {
      ...(surface.preview_diff || {}),
      selected_overrides: surface.override_count,
    };
  }
  if (action === "reset") {
    const confirmed = window.confirm(app.locale === "ko"
      ? "덱 전체 마스터 스타일을 기본값으로 되돌릴까요?"
      : "Reset the deck-wide Master Style to its default?");
    if (!confirmed) {
      app.undoStack.pop();
      return;
    }
    if (app.baselineStyleData) {
      app.data.theme_tokens = clone(app.baselineStyleData.theme_tokens);
      app.data.text_style_roles = clone(app.baselineStyleData.text_style_roles);
      app.data.master_styles = clone(app.baselineStyleData.master_styles);
    }
    surface.active_style_id = app.data.master_styles?.[0]?.master_style_id || "master-style-commercial-mvp-v1";
    surface.selected_palette_id = "baseline";
    surface.type_scale_id = "standard";
    surface.shape_radius = app.data.master_styles?.[0]?.shape_defaults?.radius || 8;
    surface.locked = false;
    surface.override_count = 0;
    surface.preview_diff = { palette_changed: false, typography_changed: false, shape_defaults_changed: false, selected_overrides: 0 };
    document.querySelector('[data-action="master-lock"]')?.setAttribute("aria-pressed", "false");
    applyThemeToDeckObjects();
  }
  recordOperation("master_style_update", { summary: `master style ${action}` });
  renderAll();
  openFeatureSurface("master-style");
  showCommandFeedback(app.locale === "ko" ? `마스터 스타일 ${localizedValue(action)} 완료` : `Master Style ${action} complete.`);
}

function importReferenceRecipes() {
  const library = app.data.reference_design_library || {};
  library.importer ||= {};
  library.importer.last_import_status = "content_free_recipes_ready";
  library.importer.last_import_recipe_count = library.recipes?.length || 0;
  library.apply_flow ||= {
    before_after_summary: app.locale === "ko"
      ? "가져오기 완료: 팔레트/타입/레이아웃/컴포넌트 레시피만 준비되었습니다. 원본 내용은 제외되었습니다."
      : "Import complete: palette, type, layout, and component recipes are ready. Source content is excluded.",
    affected_tokens: ["palette", "typography", "layout_recipe", "component_recipe"],
    undo_available: true,
    reset_available: true,
    content_excluded: true,
  };
  recordOperation("reference_design_import", { summary: "content-free reference design recipes imported" });
  renderCommercialScaffolds();
  showCommandFeedback(app.locale === "ko" ? "원본 내용 없이 디자인 레시피를 가져왔습니다." : "Design recipes imported without source content.");
}

function resetStyleMemory() {
  const profile = styleMemoryProfile();
  if (!profile) return;
  const confirmed = window.confirm(app.locale === "ko"
    ? "스타일 메모리 선호값을 초기화할까요? 실행 취소와는 별개입니다."
    : "Reset Style Memory preferences? This is separate from undo/redo.");
  if (!confirmed) return;
  pushHistory("reset style memory");
  profile.preferences = {
    preferred_text_role_refs: [],
    preferred_palette_refs: [],
    accepted_layout_recipe_refs: [],
    rejected_layout_recipe_refs: [],
    density_preference: "unset",
    logo_placement: "unset",
    font_preference: "unset",
    recurring_local_edits: [],
  };
  profile.public_handoff_summary.preference_count = 0;
  recordOperation("style_memory_reset", { summary: "user reset public-safe style memory profile" });
  renderCommercialScaffolds();
  showCommandFeedback(app.locale === "ko" ? "스타일 메모리를 초기화했습니다." : "Style Memory reset.");
}

function deleteStyleMemory() {
  if (!app.data.style_memory_profiles?.length) return;
  const confirmed = window.confirm(app.locale === "ko"
    ? "스타일 메모리를 삭제할까요? 숨은 모델 메모리나 실행 취소 기록은 아닙니다."
    : "Delete Style Memory? It is not hidden model memory or undo history.");
  if (!confirmed) return;
  pushHistory("delete style memory");
  app.data.style_memory_profiles = [];
  recordOperation("style_memory_delete", { summary: "user deleted public-safe style memory profile" });
  renderCommercialScaffolds();
  showCommandFeedback(app.locale === "ko" ? "스타일 메모리를 삭제했습니다." : "Style Memory deleted.");
}

function canvasPoint(event) {
  const rect = refs.canvas.getBoundingClientRect();
  return {
    x: (event.clientX - rect.left) / app.scale,
    y: (event.clientY - rect.top) / app.scale,
  };
}

function startObjectDrag(event, objectId) {
  const object = activeSlide().objects.find((item) => item.id === objectId);
  if (!object) return;
  pushHistory("move object");
  const point = canvasPoint(event);
  app.drag = {
    objectId,
    startX: point.x,
    startY: point.y,
    objectX: object.x,
    objectY: object.y,
    moved: false,
  };
  try {
    event.currentTarget.setPointerCapture?.(event.pointerId);
  } catch {
    // Synthetic smoke events and some browser-generated pointer transitions do not own capture.
  }
}

function startResize(event, objectId, handle) {
  const object = activeSlide().objects.find((item) => item.id === objectId);
  if (!object) return;
  pushHistory("resize object");
  const point = canvasPoint(event);
  app.resize = {
    objectId,
    handle,
    startX: point.x,
    startY: point.y,
    object: clone(object),
    moved: false,
  };
  try {
    event.currentTarget.setPointerCapture?.(event.pointerId);
  } catch {
    // Synthetic smoke events and some browser-generated pointer transitions do not own capture.
  }
}

function onPointerMove(event) {
  if (app.drag) {
    const object = activeSlide().objects.find((item) => item.id === app.drag.objectId);
    if (!object) return;
    const point = canvasPoint(event);
    const dx = point.x - app.drag.startX;
    const dy = point.y - app.drag.startY;
    object.x = Math.round(clamp(app.drag.objectX + dx, -object.w + 24, CANVAS_WIDTH - 24));
    object.y = Math.round(clamp(app.drag.objectY + dy, -object.h + 24, CANVAS_HEIGHT - 24));
    app.drag.moved = Math.abs(dx) + Math.abs(dy) > 2;
    renderCanvas();
  }
  if (app.resize) {
    const object = activeSlide().objects.find((item) => item.id === app.resize.objectId);
    if (!object) return;
    const point = canvasPoint(event);
    const dx = point.x - app.resize.startX;
    const dy = point.y - app.resize.startY;
    const original = app.resize.object;
    if (app.resize.handle.includes("e")) object.w = Math.round(Math.max(MIN_OBJECT_SIZE, original.w + dx));
    if (app.resize.handle.includes("s")) object.h = Math.round(Math.max(MIN_OBJECT_SIZE, original.h + dy));
    if (app.resize.handle.includes("w")) {
      object.x = Math.round(original.x + dx);
      object.w = Math.round(Math.max(MIN_OBJECT_SIZE, original.w - dx));
    }
    if (app.resize.handle.includes("n")) {
      object.y = Math.round(original.y + dy);
      object.h = Math.round(Math.max(MIN_OBJECT_SIZE, original.h - dy));
    }
    object.x = Math.round(clamp(object.x, -object.w + 24, CANVAS_WIDTH - 24));
    object.y = Math.round(clamp(object.y, -object.h + 24, CANVAS_HEIGHT - 24));
    app.resize.moved = true;
    renderCanvas();
  }
}

function onPointerUp() {
  if (app.drag) {
    if (app.drag.moved) {
      recordOperation("move_object", { object_id: app.drag.objectId, summary: "object moved on canvas" });
    } else {
      app.undoStack.pop();
    }
    app.drag = null;
  }
  if (app.resize) {
    if (app.resize.moved) {
      recordOperation("resize_object", { object_id: app.resize.objectId, summary: "object resized on canvas" });
    } else {
      app.undoStack.pop();
    }
    app.resize = null;
  }
}

function beginInlineTextEdit(objectId) {
  const object = activeSlide().objects.find((item) => item.id === objectId);
  if (!object || object.type !== "text") return;
  if (app.editingObjectId && app.editingObjectId !== objectId) commitInlineTextEdit();
  pushHistory("edit text");
  app.editingObjectId = objectId;
  app.activeTextSelection = null;
  const el = refs.canvas.querySelector(`[data-object-id="${CSS.escape(objectId)}"]`);
  if (!el) return;
  el.setAttribute("contenteditable", "true");
  el.replaceChildren(document.createTextNode(plainText(object)));
  el.focus();
  document.getSelection()?.selectAllChildren(el);
  el.addEventListener("input", onInlineTextInput);
  el.addEventListener("mouseup", captureActiveTextSelection);
  el.addEventListener("keyup", captureActiveTextSelection);
  app.inlineEditBlurHandler = () => commitInlineTextEdit();
  app.inlineEditKeyHandler = (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      commitInlineTextEdit();
    } else if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      commitInlineTextEdit();
    }
  };
  el.addEventListener("blur", app.inlineEditBlurHandler);
  el.addEventListener("keydown", app.inlineEditKeyHandler);
}

function onInlineTextInput(event) {
  const object = activeSlide().objects.find((item) => item.id === app.editingObjectId);
  if (!object) return;
  setObjectText(object, event.currentTarget.textContent || "");
  refs.textEditor.value = plainText(object);
  markSaved("Editing text");
}

function commitInlineTextEdit() {
  const objectId = app.editingObjectId;
  if (!objectId) return;
  const el = refs.canvas.querySelector(`[data-object-id="${CSS.escape(objectId)}"]`);
  const object = activeSlide().objects.find((item) => item.id === objectId);
  if (el) {
    el.removeAttribute("contenteditable");
    el.removeEventListener("input", onInlineTextInput);
    el.removeEventListener("mouseup", captureActiveTextSelection);
    el.removeEventListener("keyup", captureActiveTextSelection);
    if (app.inlineEditBlurHandler) el.removeEventListener("blur", app.inlineEditBlurHandler);
    if (app.inlineEditKeyHandler) el.removeEventListener("keydown", app.inlineEditKeyHandler);
  }
  if (object && el) setObjectText(object, el.textContent || "");
  app.editingObjectId = null;
  app.inlineEditBlurHandler = null;
  app.inlineEditKeyHandler = null;
  recordOperation("edit_text", { object_id: objectId, object_type: "text", summary: "canvas text edited directly" });
  renderCanvas();
}

function handlePlainTextPaste(event) {
  event.preventDefault();
  const text = event.clipboardData?.getData("text/plain") || "";
  document.execCommand("insertText", false, text);
}

function captureActiveTextSelection() {
  if (!app.editingObjectId) return;
  const el = refs.canvas.querySelector(`[data-object-id="${CSS.escape(app.editingObjectId)}"]`);
  const selection = document.getSelection();
  if (!el || !selection || selection.rangeCount === 0) return;
  const range = selection.getRangeAt(0);
  if (!el.contains(range.commonAncestorContainer) || range.collapsed) return;
  const before = range.cloneRange();
  before.selectNodeContents(el);
  before.setEnd(range.startContainer, range.startOffset);
  const start = before.toString().length;
  const length = range.toString().length;
  app.activeTextSelection = { objectId: app.editingObjectId, start, end: start + length };
}

function styleRunsForRange(object, stylePatch) {
  const text = plainText(object);
  const selection = app.activeTextSelection?.objectId === object.id ? app.activeTextSelection : null;
  const start = selection ? selection.start : 0;
  const end = selection ? selection.end : text.length;
  if (end <= start) return false;
  const baseRun = object.paragraphs?.[0]?.runs?.[0] || {};
  const before = text.slice(0, start);
  const selected = text.slice(start, end);
  const after = text.slice(end);
  const runs = [];
  if (before) runs.push({ ...baseRun, text: before });
  runs.push({ ...baseRun, ...stylePatch, text: selected });
  if (after) runs.push({ ...baseRun, text: after });
  object.paragraphs = [{
    role: object.textRole || "Body",
    alignment: object.textAlign || "left",
    bullet: false,
    bulletLevel: 0,
    spacingAfter: 4,
    overflowPolicy: "wrap",
    runs,
  }];
  object.text = text;
  return true;
}

function patchCoversWholeText(object) {
  const text = plainText(object);
  const selection = app.activeTextSelection?.objectId === object.id ? app.activeTextSelection : null;
  return !selection || (selection.start <= 0 && selection.end >= text.length);
}

function applyObjectTextDefaults(object, patch) {
  for (const key of ["fontFamilyToken", "fontSize", "fontWeight", "color"]) {
    if (patch[key] !== undefined) object[key] = patch[key];
  }
}

function applyTextRole(role) {
  const object = selectedObject();
  if (!object || object.type !== "text" || !app.data.text_style_roles[role]) {
    showCommandFeedback("Select one text object first.");
    return;
  }
  pushHistory("apply text role");
  const defaults = app.data.text_style_roles[role];
  object.textRole = role;
  object.fontFamilyToken = defaults.fontFamilyToken;
  object.fontSize = defaults.fontSize;
  object.fontWeight = defaults.fontWeight;
  object.color = defaults.color;
  object.lineHeight = defaults.lineHeight;
  object.paragraphs = (object.paragraphs || textToParagraphs(object.text || "", object)).map((paragraph) => ({
    ...paragraph,
    role,
    bullet: role === "Bullet" ? true : paragraph.bullet,
    runs: (paragraph.runs || []).map((run) => ({
      ...run,
      fontFamilyToken: defaults.fontFamilyToken,
      fontSize: defaults.fontSize,
      fontWeight: defaults.fontWeight,
      color: defaults.color,
    })),
  }));
  recordOperation("apply_text_role", { object_id: object.id, object_type: "text", summary: `text role ${role} applied` });
  renderCanvas();
}

function applyRichTextPatch(patch) {
  const editingId = app.editingObjectId;
  if (editingId) {
    captureActiveTextSelection();
    commitInlineTextEdit();
    setSelection([editingId]);
  }
  const object = selectedObject();
  if (!object || object.type !== "text") {
    showCommandFeedback("Text styling needs one selected text box.");
    return;
  }
  pushHistory("apply rich text run");
  const updateObjectDefaults = patchCoversWholeText(object);
  if (styleRunsForRange(object, patch)) {
    if (updateObjectDefaults) applyObjectTextDefaults(object, patch);
    recordOperation("edit_rich_text_run", { object_id: object.id, object_type: "text", summary: "selected text range styled" });
    renderCanvas();
  } else {
    app.undoStack.pop();
  }
}

function toggleBullet() {
  const object = selectedObject();
  if (!object || object.type !== "text") {
    showCommandFeedback("Bullet state applies to one selected text box.");
    return;
  }
  pushHistory("toggle bullet");
  object.paragraphs = (object.paragraphs || textToParagraphs(object.text || "", object)).map((paragraph) => ({
    ...paragraph,
    role: paragraph.bullet ? object.textRole || "Body" : "Bullet",
    bullet: !paragraph.bullet,
    bulletLevel: paragraph.bullet ? 0 : Math.min(2, paragraph.bulletLevel || 0),
  }));
  recordOperation("toggle_bullet", { object_id: object.id, object_type: "text", summary: "paragraph-level bullet state toggled" });
  renderCanvas();
}

function alignText(alignment) {
  const object = selectedObject();
  if (!object || object.type !== "text") {
    showCommandFeedback("Text alignment needs one selected text box.");
    return;
  }
  pushHistory("align text");
  object.textAlign = alignment;
  object.paragraphs = (object.paragraphs || []).map((paragraph) => ({ ...paragraph, alignment }));
  recordOperation("align_text", { object_id: object.id, object_type: "text", summary: `text aligned ${alignment}` });
  renderCanvas();
}

function updateGeometryFromInputs() {
  const object = selectedObject();
  if (!object) return;
  const next = {
    x: Number(refs.geometry.x.value),
    y: Number(refs.geometry.y.value),
    w: Number(refs.geometry.w.value),
    h: Number(refs.geometry.h.value),
  };
  if (!Object.values(next).every((value) => Number.isFinite(value))) return;
  if (next.w <= 0 || next.h <= 0) return;
  if (
    Math.round(object.x) === Math.round(next.x) &&
    Math.round(object.y) === Math.round(next.y) &&
    Math.round(object.w) === Math.round(next.w) &&
    Math.round(object.h) === Math.round(next.h)
  ) {
    return;
  }
  pushHistory("edit geometry");
  object.x = next.x;
  object.y = next.y;
  object.w = Math.max(MIN_OBJECT_SIZE, next.w);
  object.h = Math.max(MIN_OBJECT_SIZE, next.h);
  recordOperation("edit_geometry", { summary: "geometry changed in inspector" });
  renderCanvas();
}

function applyInspectorText() {
  const object = selectedObject();
  if (!object || object.type !== "text") {
    showCommandFeedback("Select one text object before applying inspector text.");
    return;
  }
  if (plainText(object) === refs.textEditor.value) return;
  pushHistory("apply text");
  setObjectText(object, refs.textEditor.value);
  recordOperation("edit_text", { object_id: object.id, object_type: "text", summary: "text changed from inspector" });
  renderCanvas();
}

function duplicateSelectedObject() {
  const object = selectedObject();
  if (!object) {
    showCommandFeedback("Select one object to duplicate.");
    return;
  }
  pushHistory("duplicate object");
  const copy = clone(object);
  copy.id = `${object.id}-copy-${Date.now().toString(36).slice(-5)}`;
  copy.x = Math.round(object.x + 36);
  copy.y = Math.round(object.y + 36);
  copy.z = highestZ(activeSlide()) + 1;
  activeSlide().objects.push(copy);
  setSelection([copy.id]);
  recordOperation("duplicate_object", { object_id: copy.id, object_type: copy.type, summary: "object duplicated" });
  renderAll();
}

function deleteSelectedObject() {
  if (!app.selectedObjectIds.length) {
    showCommandFeedback("Select an object to delete.");
    return;
  }
  pushHistory("delete object");
  const slide = activeSlide();
  const removed = selectedObjects();
  slide.objects = slide.objects.filter((item) => !app.selectedObjectIds.includes(item.id));
  recordOperation("delete_object", { object_id: removed[0]?.id, object_type: removed[0]?.type, summary: `${removed.length} object(s) deleted` });
  setSelection([]);
  renderAll();
}

function highestZ(slide) {
  return Math.max(1, ...slide.objects.map((object) => object.z || 1));
}

function changeZOrder(direction) {
  const object = selectedObject();
  if (!object) {
    showCommandFeedback("Select one object before changing layer order.");
    return;
  }
  pushHistory("change z order");
  object.z = Math.max(1, (object.z || 1) + direction);
  recordOperation(direction > 0 ? "bring_forward" : "send_backward", {
    object_id: object.id,
    object_type: object.type,
    summary: direction > 0 ? "object moved forward" : "object moved backward",
  });
  renderCanvas();
}

function selectionBounds(objects) {
  return {
    x: Math.min(...objects.map((object) => object.x)),
    y: Math.min(...objects.map((object) => object.y)),
    right: Math.max(...objects.map((object) => object.x + object.w)),
    bottom: Math.max(...objects.map((object) => object.y + object.h)),
  };
}

function alignSelected(kind) {
  const objects = selectedObjects();
  if (!objects.length) {
    showCommandFeedback("Select at least one object to align.");
    return;
  }
  pushHistory("align object");
  const target = refs.alignTarget.value === "slide"
    ? { x: 96, y: 72, right: CANVAS_WIDTH - 96, bottom: CANVAS_HEIGHT - 72 }
    : selectionBounds(objects);
  for (const object of objects) {
    if (kind === "left") object.x = target.x;
    if (kind === "center") object.x = Math.round((target.x + target.right - object.w) / 2);
    if (kind === "right") object.x = Math.round(target.right - object.w);
    if (kind === "top") object.y = target.y;
    if (kind === "middle") object.y = Math.round((target.y + target.bottom - object.h) / 2);
    if (kind === "bottom") object.y = Math.round(target.bottom - object.h);
  }
  recordOperation("align_object", { object_id: objects[0].id, object_type: objects[0].type, summary: `${objects.length} object(s) aligned ${kind}` });
  renderCanvas();
}

function distributeSelected(axis) {
  const objects = selectedObjects();
  if (objects.length < 3) {
    showCommandFeedback("Distribute needs three or more selected objects.");
    return;
  }
  pushHistory("distribute objects");
  const sorted = [...objects].sort((a, b) => axis === "horizontal" ? a.x - b.x : a.y - b.y);
  const first = sorted[0];
  const last = sorted[sorted.length - 1];
  const span = axis === "horizontal" ? last.x - first.x : last.y - first.y;
  const step = span / (sorted.length - 1);
  sorted.forEach((object, index) => {
    if (axis === "horizontal") object.x = Math.round(first.x + step * index);
    else object.y = Math.round(first.y + step * index);
  });
  recordOperation("distribute_object", { object_id: sorted[0].id, object_type: sorted[0].type, summary: `${objects.length} object(s) distributed ${axis}` });
  renderCanvas();
}

function addTextObject() {
  pushHistory("add text");
  const slide = activeSlide();
  const object = {
    id: `text-${Date.now().toString(36)}`,
    type: "text",
    x: 160,
    y: 180,
    w: 420,
    h: 120,
    z: highestZ(slide) + 1,
    text: "새 텍스트를 입력하세요",
    fontSize: 30,
    fontWeight: 700,
    color: "#151515",
    lineHeight: 1.22,
    fill: "#FFFFFF",
    radius: 8,
    textRole: "Body",
    fontFamilyToken: "body",
    paragraphs: [],
  };
  setObjectText(object, object.text);
  slide.objects.push(object);
  setSelection([object.id]);
  recordOperation("add_text", { object_id: object.id, object_type: "text", summary: "text box added" });
  renderAll();
}

function addShapeObject() {
  pushHistory("add shape");
  const slide = activeSlide();
  const object = {
    id: `shape-${Date.now().toString(36)}`,
    type: "shape",
    shape: "rect",
    x: 220,
    y: 250,
    w: 260,
    h: 150,
    z: highestZ(slide) + 1,
    fill: "#F2D76B",
    stroke: "#132326",
    radius: 8,
  };
  slide.objects.push(object);
  setSelection([object.id]);
  recordOperation("add_shape", { object_id: object.id, object_type: "shape", summary: "shape added" });
  renderAll();
}

function transformSelected(kind, value = 0) {
  const objects = selectedObjects().filter((object) => object.type === "shape" || object.type === "image");
  if (!objects.length) {
    showCommandFeedback(kind === "radius" ? "Radius applies only to shapes." : "Rotate and flip apply only to shapes or image slots.");
    return;
  }
  pushHistory("transform object");
  let changed = false;
  for (const object of objects) {
    if (kind === "rotate") {
      object.rotation = Math.round(((object.rotation || 0) + value) % 360);
      changed = true;
    }
    if (kind === "reset") {
      object.rotation = 0;
      changed = true;
    }
    if (kind === "flipX") {
      object.flipX = !object.flipX;
      changed = true;
    }
    if (kind === "flipY") {
      object.flipY = !object.flipY;
      changed = true;
    }
    if (kind === "radius" && object.type === "shape") {
      object.radius = clamp(Number(value), 0, 96);
      changed = true;
    }
  }
  if (!changed) {
    app.undoStack.pop();
    showCommandFeedback("That command is not available for this selection.");
    return;
  }
  recordOperation("transform_object", { object_id: objects[0].id, object_type: objects[0].type, summary: `${objects.length} shape/image transform ${kind}` });
  renderCanvas();
}

function setZoom(mode) {
  if (mode === "fit") {
    app.zoomMode = "fit";
  } else {
    app.zoomMode = "manual";
    app.manualZoom = clamp(app.scale + (mode === "in" ? 0.1 : -0.1), 0.28, 1.4);
  }
  updateCanvasScale();
  recordOperation("zoom_canvas", { summary: app.zoomMode === "fit" ? "canvas fit enabled" : `canvas zoom ${Math.round(app.manualZoom * 100)} percent` });
}

function toggleTheme() {
  app.theme = app.theme === "light" ? "dark" : "light";
  $(".workbench-shell").dataset.theme = app.theme;
  recordOperation("toggle_theme", { summary: `${app.theme} app chrome enabled` });
}

function setLabelPrefix(label, text) {
  if (!label) return;
  const node = Array.from(label.childNodes).find((child) => child.nodeType === Node.TEXT_NODE);
  if (node) node.textContent = `${text} `;
}

function setText(selector, text) {
  const node = $(selector);
  if (node) node.textContent = text;
}

function applyActionLabels(text) {
  Object.entries(text.actions).forEach(([action, [label, visible]]) => {
    const button = document.querySelector(`[data-action="${action}"]`);
    if (!button) return;
    button.setAttribute("title", label);
    button.setAttribute("aria-label", label);
    button.textContent = visible;
  });
}

function applySelectLabels() {
  const ko = app.locale === "ko";
  const fontLabels = {
    heading: ko ? "제목" : "Heading",
    body: ko ? "본문" : "Body",
    caption: ko ? "캡션" : "Caption",
  };
  Array.from(refs.textFont?.options || []).forEach((option) => {
    option.textContent = fontLabels[option.value] || option.textContent;
  });
  const alignLabels = {
    selection: ko ? "선택 항목" : "Selection",
    slide: ko ? "슬라이드" : "Slide",
  };
  Array.from(refs.alignTarget?.options || []).forEach((option) => {
    option.textContent = alignLabels[option.value] || option.textContent;
  });
  const paletteLabels = {
    baseline: ko ? "뉴트럴 옐로" : "Neutral yellow",
    contrast: ko ? "고대비" : "High contrast",
    editorial: ko ? "에디토리얼 그린" : "Editorial green",
  };
  Array.from(refs.masterPalette?.options || []).forEach((option) => {
    option.textContent = paletteLabels[option.value] || option.textContent;
  });
  const scaleLabels = {
    standard: ko ? "표준" : "Standard",
    compact: ko ? "압축" : "Compact",
    spacious: ko ? "여유" : "Spacious",
  };
  Array.from(refs.masterTypeScale?.options || []).forEach((option) => {
    option.textContent = scaleLabels[option.value] || option.textContent;
  });
  const radiusLabels = {
    "4": ko ? "또렷함" : "Crisp",
    "8": ko ? "기본" : "Default",
    "16": ko ? "부드러움" : "Soft",
  };
  Array.from(refs.masterRadius?.options || []).forEach((option) => {
    option.textContent = radiusLabels[option.value] || option.textContent;
  });
}

function applyLocaleText() {
  const text = UI_TEXT[app.locale];
  applyActionLabels(text);
  applySelectLabels();
  document.querySelector('[data-action="toggle-theme"]').textContent = text.buttons.toggleTheme;
  document.querySelector('[data-surface="master-style"]').textContent = text.buttons.masterStyle;
  document.querySelector('[data-surface="design-library"]').textContent = text.buttons.designLibrary;
  document.querySelector('[data-surface="memory-share"]').textContent = text.buttons.memoryShare;
  document.querySelector('[data-action="export-pdf"]').textContent = text.buttons.exportPdf;
  document.querySelector('[data-action="export-pptx"]').textContent = text.buttons.exportPptx;
  document.querySelector('[data-surface="export-handoff"]').textContent = text.buttons.exportStatus;
  document.querySelector('[data-action="close-surface"]').textContent = text.close;
  document.querySelector('[data-action="apply-text"]').textContent = text.buttons.applyText;
  document.querySelector('[data-action="import-reference-recipes"]').textContent = text.buttons.importRecipes;
  document.querySelector('[data-action="reset-reference-recipe"]').textContent = text.buttons.resetRecipe;
  document.querySelector('[data-action="proposal-ready"]').textContent = text.buttons.proposalReady;
  document.querySelector('[data-action="blocked"]').textContent = text.buttons.blocked;
  document.querySelector('[data-action="final-received"]').textContent = text.buttons.finalReceived;
  document.querySelector('[data-mode="assistant"]').textContent = text.mode.assistant;
  document.querySelector('[data-mode="auto"]').textContent = text.mode.auto;
  refs.saveStatus.textContent = text.labels.saved;
  setText(".feature-surface-header .eyebrow", text.deckSurface);
  setText(".slide-rail .eyebrow", text.labels.slides);
  setText(".stage-heading .eyebrow", text.labels.canvas);
  setText(".inspector .eyebrow", text.labels.properties);
  setText(".inspector .field-block:nth-of-type(1) h3", text.labels.positionSize);
  setText(".inspector .field-block:nth-of-type(2) h3", text.labels.text);
  setText(".inspector .field-block:nth-of-type(3) h3", text.labels.resolvedStyle);
  refs.textEditor.placeholder = app.locale === "ko"
    ? "캔버스의 텍스트를 두 번 클릭해 직접 편집하세요."
    : "Double-click text on the canvas to edit directly.";
  setLabelPrefix(document.querySelector('label:has(#text-role)'), text.labels.role);
  setLabelPrefix(document.querySelector('label:has(#text-font)'), text.labels.font);
  setLabelPrefix(document.querySelector('label:has(#text-size)'), text.labels.size);
  setLabelPrefix(document.querySelector('label:has(#text-color)'), text.labels.color);
  setLabelPrefix(document.querySelector('label:has(#shape-radius)'), text.labels.radius);
  setLabelPrefix(document.querySelector('label:has(#align-target)'), text.labels.alignTo);
  const headings = {
    '[data-feature-panel="master-style"] h3': app.locale === "ko" ? "테마와 마스터 스타일" : "Theme and master style",
    '[data-feature-panel="design-library"] h3': app.locale === "ko" ? "레퍼런스 디자인 라이브러리" : "Reference Design Library",
    '[data-feature-panel="design-library"] div:nth-of-type(2) h3': app.locale === "ko" ? "에셋 시스템 준비 상태" : "Asset-system readiness",
    '[data-feature-panel="memory-share"] div:nth-of-type(1) h3': app.locale === "ko" ? "AI 수정 메모리" : "AI revision memory",
    '[data-feature-panel="memory-share"] div:nth-of-type(2) h3': app.locale === "ko" ? "스타일 메모리" : "Style Memory",
    '[data-feature-panel="memory-share"] div:nth-of-type(3) h3': app.locale === "ko" ? "게시 뷰어" : "Published viewer",
    '[data-feature-panel="memory-share"] div:nth-of-type(4) h3': app.locale === "ko" ? "추천과 크레딧" : "Referral and credits",
    '[data-feature-panel="export-handoff"] h3': app.locale === "ko" ? "Host-AI 내보내기 핸드오프" : "Host-AI export handoff",
  };
  Object.entries(headings).forEach(([selector, value]) => setText(selector, value));
  const summaries = $$("[data-feature-panel] .summary-text");
  if (summaries[0]) summaries[0].textContent = app.locale === "ko"
    ? "덱 전체 타이포그래피, 팔레트, 도형 기본값, 슬라이드 장식을 여기서 관리합니다. 인스펙터는 선택 오브젝트의 적용 스타일만 보여줍니다."
    : "Deck-level typography, palette, shape defaults, and slide chrome live here. The inspector only shows the selected object's resolved role.";
  if (summaries[1]) summaries[1].textContent = app.locale === "ko"
    ? "로컬 호스트 AI는 IR, 세일즈, 포트폴리오 벤치마크군에서 내용 없는 레시피만 가져옵니다."
    : "Local host AI may import only content-free recipes from IR, sales, and portfolio benchmark families.";
  if (summaries[2]) summaries[2].textContent = app.locale === "ko"
    ? "에셋 시스템 연결 준비는 되어 있지만 실제 디자인 패키지는 아직 연결되지 않았습니다."
    : "Asset-system connection is ready, but no real design package is connected yet.";
  const activeSurface = refs.featureSurface.dataset.activeSurface;
  if (activeSurface) refs.featureSurfaceTitle.textContent = text.surfaces[activeSurface];
  if (app.data?.export_hooks?.current_status) {
    refs.exportStatus.textContent = text.status[app.data.export_hooks.current_status] || app.data.export_hooks.current_status;
    refs.exportSummary.textContent = text.exportMessages[app.exportMessageKey] || refs.exportSummary.textContent;
  }
  updateInspector();
  if (app.data) {
    renderStyleSummary();
    renderCommercialScaffolds();
  }
  updateCanvasScale();
  setMode(app.mode);
}

function setLocale(locale) {
  if (!["ko", "en"].includes(locale)) return;
  app.locale = locale;
  document.documentElement.lang = locale;
  $$("[data-locale]").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.locale === locale)));
  applyLocaleText();
  recordOperation("switch_locale", { summary: `${locale} UI labels selected` });
}

function undo() {
  const snapshot = app.undoStack.pop();
  if (!snapshot) return;
  app.redoStack.push({
    label: "redo",
    deck: clone(app.deck),
    activeSlideIndex: app.activeSlideIndex,
    selectedObjectId: app.selectedObjectId,
    selectedObjectIds: clone(app.selectedObjectIds),
  });
  restoreSnapshot(snapshot);
  recordOperation("undo", { summary: "undo restored prior local state" });
}

function redo() {
  const snapshot = app.redoStack.pop();
  if (!snapshot) return;
  app.undoStack.push({
    label: "undo",
    deck: clone(app.deck),
    activeSlideIndex: app.activeSlideIndex,
    selectedObjectId: app.selectedObjectId,
    selectedObjectIds: clone(app.selectedObjectIds),
  });
  restoreSnapshot(snapshot);
  recordOperation("redo", { summary: "redo restored local edit" });
}

function createExportEnvelope(kind) {
  return {
    envelope_version: "commercial_mvp_host_ai_export_handoff.v1",
    target_export_kind: kind,
    safe_project_label: "A.DreamMaker PPT Maker",
    safe_deck_label: app.deck.safe_label,
    selected_slide_id: activeSlide().id,
    scope: "all_slides",
    mode: app.mode,
    design_guide_version: app.data.design_guide_package.version,
    design_package_ref: {
      design_package_id: app.data.design_package.design_package_id,
      manifest_hash: app.data.design_package.manifest_hash,
      source_kind: app.data.design_package.source_kind,
      theme_id: app.data.theme_tokens.theme_id,
      master_style_id: app.data.master_styles?.[0]?.master_style_id,
      token_set_id: app.data.theme_tokens.token_set_id,
    },
    work_state_reference: safeWorkStateReference(),
    sanitized_operation_summary: sanitizedOperationSummary(),
    approved_asset_refs: summarizeTransforms()
      .filter((item) => item.safeRef)
      .map((item) => ({ slide_id: item.slide_id, object_id: item.object_id, safeRef: item.safeRef })),
    text_roles: Object.keys(app.data.text_style_roles),
    revision_memory: app.revisionMemory.slice(-8).map(({ memory_id, kind, mode, summary }) => ({ memory_id, kind, mode, summary })),
    reference_design_library: referenceDesignHandoffSummary(),
    style_memory: styleMemoryHandoffSummary(),
    published_views: publishedViewHandoffSummary(),
    referral_entitlement: referralCreditHandoffSummary(),
    safe_asset_design_refs: safeAssetDesignRefs(),
    quality_requirements: [
      "fixed 16:9 canvas",
      "Korean wrapping must remain readable",
      "do not claim final output unless a real result reference exists"
    ],
    forbidden_content_absent: true,
  };
}

function setExportState(state, message, messageKey = state) {
  if (!app.data.export_hooks.allowed_statuses.includes(state)) return;
  refs.exportStatus.textContent = UI_TEXT[app.locale].status[state] || state;
  refs.exportStatus.dataset.exportState = state;
  app.exportMessageKey = messageKey;
  refs.exportSummary.textContent = message || UI_TEXT[app.locale].exportMessages[messageKey] || state;
  app.data.export_hooks.current_status = state;
  renderWorkStateSummary();
}

function handleExport(kind) {
  pushHistory(`export ${kind}`);
  app.activeExportEnvelope = createExportEnvelope(kind);
  app.revisionMemory.push({
    memory_id: `revmem-${kind}-${Date.now().toString(36)}`,
    kind: "export_handoff",
    mode: app.mode,
    summary: `${kind} handoff sent without final-result claim`,
    undo_redo_independent: true,
  });
  recordOperation("export_handoff_created", {
    object_id: null,
    object_type: null,
    summary: `${kind} handoff envelope created`,
  });
  setExportState("handoff_sent", `${kind.toUpperCase()} ${UI_TEXT[app.locale].exportMessages.handoff_sent}`, "handoff_sent");
  openFeatureSurface("export-handoff");
  window.setTimeout(() => {
    if (app.data.export_hooks.current_status === "handoff_sent") {
      setExportState("awaiting_host_ai", UI_TEXT[app.locale].exportMessages.awaiting_host_ai, "awaiting_host_ai");
    }
  }, 350);
  renderDiagnostics();
  renderRevisionMemory();
}

function proposalReady() {
  setExportState("proposal_ready", UI_TEXT[app.locale].exportMessages.proposal_ready, "proposal_ready");
  recordOperation("export_proposal_ready", { summary: "host AI proposal status set" });
}

function blockedExport() {
  setExportState("blocked", UI_TEXT[app.locale].exportMessages.blocked, "blocked");
  recordOperation("export_blocked", { summary: "host AI export blocked without private details" });
}

function finalReceived() {
  if (!app.data.export_hooks.real_host_result_ref) {
    setExportState("awaiting_host_ai", UI_TEXT[app.locale].exportMessages.final_missing, "final_missing");
    return;
  }
  setExportState("final_received", UI_TEXT[app.locale].exportMessages.final_received, "final_received");
}

function handleAction(action, trigger = null) {
  if (action === "undo") undo();
  if (action === "redo") redo();
  if (action === "duplicate-object") duplicateSelectedObject();
  if (action === "delete-object") deleteSelectedObject();
  if (action === "bring-forward") changeZOrder(1);
  if (action === "send-backward") changeZOrder(-1);
  if (action === "align-left") alignSelected("left");
  if (action === "align-center") alignSelected("center");
  if (action === "align-right") alignSelected("right");
  if (action === "align-top") alignSelected("top");
  if (action === "align-middle") alignSelected("middle");
  if (action === "align-bottom") alignSelected("bottom");
  if (action === "distribute-horizontal") distributeSelected("horizontal");
  if (action === "distribute-vertical") distributeSelected("vertical");
  if (action === "rotate-minus-15") transformSelected("rotate", -15);
  if (action === "rotate-plus-15") transformSelected("rotate", 15);
  if (action === "rotate-minus-90") transformSelected("rotate", -90);
  if (action === "rotate-plus-90") transformSelected("rotate", 90);
  if (action === "rotate-reset") transformSelected("reset");
  if (action === "flip-horizontal") transformSelected("flipX");
  if (action === "flip-vertical") transformSelected("flipY");
  if (action === "zoom-out") setZoom("out");
  if (action === "zoom-fit") setZoom("fit");
  if (action === "zoom-in") setZoom("in");
  if (action === "toggle-theme") toggleTheme();
  if (action === "text-bold") applyRichTextPatch({ fontWeight: 800 });
  if (action === "text-bullet") toggleBullet();
  if (action === "align-text-left") alignText("left");
  if (action === "align-text-center") alignText("center");
  if (action === "align-text-right") alignText("right");
  if (action === "add-text") addTextObject();
  if (action === "add-shape") addShapeObject();
  if (action === "apply-text") applyInspectorText();
  if (action === "export-pdf") handleExport("pdf");
  if (action === "export-pptx") handleExport("pptx");
  if (action === "proposal-ready") proposalReady();
  if (action === "blocked") blockedExport();
  if (action === "final-received") finalReceived();
  if (action === "style-memory-reset") resetStyleMemory();
  if (action === "style-memory-delete") deleteStyleMemory();
  if (action === "master-apply") applyMasterStyle("apply");
  if (action === "master-override") applyMasterStyle("override");
  if (action === "master-reset") applyMasterStyle("reset");
  if (action === "master-lock") applyMasterStyle("lock");
  if (action === "import-reference-recipes") importReferenceRecipes();
  if (action === "apply-reference-recipe") applyReferenceRecipe(trigger?.dataset.family || "ir");
  if (action === "reset-reference-recipe") resetReferenceRecipe();
  if (action === "close-surface") closeFeatureSurface();
}

function bindEvents() {
  document.addEventListener("pointermove", onPointerMove);
  document.addEventListener("pointerup", onPointerUp);
  window.addEventListener("resize", updateCanvasScale);
  window.addEventListener("resize", updateFeatureSurfaceOffset);
  if ("ResizeObserver" in window) {
    new ResizeObserver(updateCanvasScale).observe(refs.canvasFrame);
  }
  refs.canvas.addEventListener("pointerdown", (event) => {
    if (event.target === refs.canvas) {
      setSelection([]);
      renderCanvas();
    }
  });
  document.addEventListener("click", (event) => {
    const action = event.target.closest("[data-action]")?.dataset.action;
    if (action) handleAction(action, event.target.closest("[data-action]"));
    const mode = event.target.closest("[data-mode]")?.dataset.mode;
    if (mode) setMode(mode);
    const locale = event.target.closest("[data-locale]")?.dataset.locale;
    if (locale) setLocale(locale);
    const surface = event.target.closest("[data-surface]")?.dataset.surface;
    if (surface) openFeatureSurface(surface);
  });
  for (const input of Object.values(refs.geometry)) {
    input.addEventListener("change", updateGeometryFromInputs);
    input.addEventListener("blur", updateGeometryFromInputs);
  }
  refs.textRole.addEventListener("change", () => applyTextRole(refs.textRole.value));
  refs.textFont.addEventListener("change", () => applyRichTextPatch({ fontFamilyToken: refs.textFont.value }));
  const applyTextSizeInput = () => {
    const size = Number(refs.textSize.value);
    const object = selectedObject();
    if (object?.type === "text" && Number.isFinite(size) && size > 0) {
      if (patchCoversWholeText(object) && Number(object.fontSize) === size) return;
      applyRichTextPatch({ fontSize: size });
    }
  };
  refs.textSize.addEventListener("change", applyTextSizeInput);
  const applyTextColorInput = () => {
    const object = selectedObject();
    if (object?.type === "text") {
      if (patchCoversWholeText(object) && object.color === refs.textColor.value) return;
      applyRichTextPatch({ color: refs.textColor.value });
    }
  };
  refs.textColor.addEventListener("change", applyTextColorInput);
  const applyRadiusInput = () => transformSelected("radius", Number(refs.shapeRadius.value));
  refs.shapeRadius.addEventListener("change", applyRadiusInput);
  [refs.masterPalette, refs.masterTypeScale, refs.masterRadius].filter(Boolean).forEach((control) => {
    control.addEventListener("change", () => {
      const surface = ensureMasterSurface();
      const settings = selectedMasterSettings();
      surface.selected_palette_id = settings.paletteId;
      surface.type_scale_id = settings.typeScaleId;
      surface.shape_radius = settings.radius;
      surface.preview_diff = {
        palette_changed: settings.paletteId !== "baseline",
        typography_changed: settings.typeScaleId !== "standard",
        shape_defaults_changed: settings.radius !== (app.baselineStyleData?.master_styles?.[0]?.shape_defaults?.radius || 8),
        selected_overrides: surface.override_count || 0,
      };
      applyThemeSettings(settings);
      renderStyleSummary();
    });
  });
  refs.textEditor.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      applyInspectorText();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (app.editingObjectId) return;
    if (isTextEntryTarget(event.target)) return;
    if (event.key === "Escape" && !refs.featureSurface.hidden) {
      event.preventDefault();
      closeFeatureSurface();
    } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
      event.preventDefault();
      undo();
    } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "y") {
      event.preventDefault();
      redo();
    } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "d") {
      event.preventDefault();
      duplicateSelectedObject();
    } else if (event.key === "Delete" || event.key === "Backspace") {
      if (app.selectedObjectId) {
        event.preventDefault();
        deleteSelectedObject();
      }
    }
  });
}

function exposeSmokeApi() {
  window.htmlWorkbenchTestApi = {
    state: app,
    get slideCount() {
      return app.deck.slides.length;
    },
    get selectedObjectId() {
      return app.selectedObjectId;
    },
    get selectedObjectIds() {
      return app.selectedObjectIds;
    },
    selectSlide(index) {
      app.activeSlideIndex = clamp(index, 0, app.deck.slides.length - 1);
      setSelection([]);
      renderAll();
    },
    selectObject(id, additive = false) {
      selectObject(id, additive);
    },
    selectObjects(ids) {
      setSelection(ids);
      renderCanvas();
    },
    loadGeneratedState(input) {
      return loadGeneratedWorkbenchState(input);
    },
    editText(id, text) {
      const object = activeSlide().objects.find((item) => item.id === id);
      if (!object || object.type !== "text") return false;
      pushHistory("api edit text");
      setObjectText(object, text);
      setSelection([id]);
      recordOperation("edit_text", { object_id: id, object_type: "text", summary: "canvas text edited directly" });
      renderAll();
      return true;
    },
    moveObject(id, dx, dy) {
      const object = activeSlide().objects.find((item) => item.id === id);
      if (!object) return false;
      pushHistory("api move object");
      object.x += dx;
      object.y += dy;
      setSelection([id]);
      recordOperation("move_object", { object_id: id, object_type: object.type, summary: "object moved on canvas" });
      renderAll();
      return true;
    },
    resizeObject(id, dw, dh) {
      const object = activeSlide().objects.find((item) => item.id === id);
      if (!object) return false;
      pushHistory("api resize object");
      object.w = Math.max(MIN_OBJECT_SIZE, object.w + dw);
      object.h = Math.max(MIN_OBJECT_SIZE, object.h + dh);
      setSelection([id]);
      recordOperation("resize_object", { object_id: id, object_type: object.type, summary: "object resized on canvas" });
      renderAll();
      return true;
    },
    applyTextRole,
    applyRichTextPatch,
    toggleBullet,
    alignSelected,
    distributeSelected,
    transformSelected,
    setZoom,
    toggleTheme,
    setLocale,
    duplicateSelectedObject,
    deleteSelectedObject,
    changeZOrder,
    handleExport,
    proposalReady,
    blockedExport,
    finalReceived,
    resetStyleMemory,
    deleteStyleMemory,
    openFeatureSurface,
    closeFeatureSurface,
    applyMasterStyle,
    referenceDesignHandoffSummary,
    styleMemoryHandoffSummary,
    publishedViewHandoffSummary,
    referralCreditHandoffSummary,
    createExportEnvelope,
    diagnosticsHidden() {
      return $("[data-dev-diagnostics]")?.hidden === true;
    },
    operationSummary: sanitizedOperationSummary,
  };
}

async function init() {
  const response = await fetch(DATA_URL);
  app.data = normalizeWorkbenchState(await response.json());
  app.baselineStyleData = {
    theme_tokens: clone(app.data.theme_tokens),
    text_style_roles: clone(app.data.text_style_roles),
    master_styles: clone(app.data.master_styles),
  };
  app.deck = clone(app.data.deck);
  app.revisionMemory = clone(app.data.revision_memory || []);
  app.mode = app.data.product_boundary.default_mode;
  bindEvents();
  exposeSmokeApi();
  applyLocaleText();
  setExportState("handoff_ready", UI_TEXT[app.locale].exportMessages.handoff_ready, "handoff_ready");
  renderAll();
}

init().catch((error) => {
  refs.canvas.textContent = `Workbench failed to load: ${error.message}`;
});
