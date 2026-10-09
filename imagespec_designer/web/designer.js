const host = window.imageSpecDesignerHost || {};
let localeMessages = {};
const tr = (key) =>
  (host.messages && host.messages[key]) || localeMessages[key] || key;
const $ = (id) => document.getElementById(id);
let profile = {
  width: 200,
  height: 120,
  rotate: 0,
  rotate_mode: "canvas",
  palette: "bw",
  background: "white",
  name: "Demo display",
  ...(host.profile || {}),
};
let doc = {
  version: 1,
  canvas: {
    width: profile.width,
    height: profile.height,
    rotate: profile.rotate,
    rotate_mode: profile.rotate_mode,
    palette: profile.palette,
    name: profile.name,
  },
  background: profile.background,
  elements: [],
};
let selected = null,
  undoStack = [],
  redoStack = [],
  metadata = [],
  geometryMetadata = {},
  templates = [],
  starterTypes = [],
  icons = {},
  scale = 3,
  dragging = null,
  dialogMode = "import",
  selectedTemplate = null,
  renderSequence = 0,
  importWarnings = [];
const api = async (name, body = {}) => {
  if (host.api) return await host.api(name, body);
  if (host[name]) return await host[name](body);
  const r = await fetch(
    `${host.apiBase || "/api"}/${name.replace(/[A-Z]/g, (m) => `-${m.toLowerCase()}`)}`,
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    },
  );
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || r.statusText);
  return data;
};
const clone = (v) => structuredClone(v);
function announce(message, error = false, warning = false) {
  $("status").textContent = message || "";
  $("status").className =
    `status${error ? " error" : warning ? " warning" : ""}`;
}
function applyTranslations() {
  const labels = {
    undo: "Undo",
    redo: "Redo",
    import: "Import YAML",
    export: "Export design YAML",
    "export-payload": "Export imagespec YAML",
    templates: "Templates",
    save: "Save",
    duplicate: "Duplicate",
    delete: "Delete",
    raise: "Raise",
    lower: "Lower",
  };
  for (const [id, key] of Object.entries(labels)) {
    const element = $(id);
    element.textContent = tr(key);
    element.title = tr(key);
  }
  $("undo").setAttribute("aria-label", tr("Undo"));
  $("redo").setAttribute("aria-label", tr("Redo"));
  $("search").placeholder = tr("Filter elements");
  document.querySelector(".tools h2").textContent = tr("Elements");
  document.querySelectorAll(".tools h2")[1].textContent = tr("Layers");
  document.querySelector(".inspector h2").textContent = tr("Properties");
}
function checkpoint() {
  undoStack.push(JSON.stringify(doc));
  if (undoStack.length > 100) undoStack.shift();
  redoStack = [];
  importWarnings = [];
  buttons();
}
function buttons() {
  $("undo").disabled = !undoStack.length;
  $("redo").disabled = !redoStack.length;
}
async function setDoc(next) {
  doc = next;
  selected = doc.elements[0]?.id || null;
  sync();
  return await render();
}
function sync() {
  $("background").value = doc.background || "white";
  $("json").value = JSON.stringify(doc, null, 2);
  drawOverlay();
  drawLayers();
  drawProperties();
}
function selectedElement() {
  return doc.elements.find((e) => e.id === selected);
}
function drawLayers() {
  const root = $("layers");
  root.replaceChildren();
  [...doc.elements].reverse().forEach((e) => {
    let b = document.createElement("button");
    b.className = `layer${e.id === selected ? " selected" : ""}`;
    b.textContent = `${e.spec.type} · ${e.id.slice(0, 7)}`;
    b.onclick = () => {
      selected = e.id;
      sync();
    };
    root.append(b);
  });
}
function drawTypes(filter = "") {
  $("types").replaceChildren();
  starterTypes
    .filter((t) => t.includes(filter.toLowerCase()))
    .forEach((type) => {
      let b = document.createElement("button");
      b.className = "type-button";
      b.textContent = `${type.replaceAll("_", " ")} +`;
      b.onclick = () => add(type);
      $("types").append(b);
    });
}
function definition(type) {
  return metadata.find((item) => item.types.includes(type));
}
function drawProperties() {
  const root = $("properties"),
    el = selectedElement();
  root.replaceChildren();
  if (!el) {
    root.innerHTML = `<p>${tr("Select an element to edit its properties.")}</p>`;
    return;
  }
  const geometry = document.createElement("div");
  geometry.innerHTML = `<strong>${tr("Position and frame")}</strong><p class="hint">${tr("Frame values are integers in canvas pixels.")}</p><div class="grid-props">${["x", "y", "width", "height"].map((k) => `<label>${k}<input data-frame="${k}" type="number" value="${el[k]}"></label>`).join("")}</div>`;
  geometry.querySelectorAll("input").forEach(
    (input) =>
      (input.onchange = () => {
        const v = Number(input.value);
        if (
          !Number.isInteger(v) ||
          ((input.dataset.frame === "width" ||
            input.dataset.frame === "height") &&
            v < 1)
        ) {
          announce(
            tr(
              "Frame values must be valid integers; dimensions must be positive",
            ),
            true,
          );
          return;
        }
        checkpoint();
        el[input.dataset.frame] = v;
        sync();
        render();
      }),
  );
  root.append(geometry);
  const fields = document.createElement("section");
  fields.className = "schema-fields";
  fields.innerHTML = `<strong>${el.spec.type.replaceAll("_", " ")} · ${tr("imagespec properties")}</strong>`;
  const schema = definition(el.spec.type);
  const supplied = geometryMetadata[el.spec.type] || { keys: [] };
  for (const field of schema?.fields || []) {
    if (
      supplied.keys.includes(field.name) &&
      !(supplied.role === "points" && field.name === "points")
    )
      continue;
    const row = document.createElement("label");
    row.className = "schema-field";
    const label = document.createElement("span");
    label.textContent = `${field.name}${field.required ? " *" : ""}`;
    if (field.doc) label.title = field.doc;
    row.append(label);
    let control;
    if (field.kind === "boolean") {
      control = document.createElement("select");
      [
        ["", "default"],
        ["true", "true"],
        ["false", "false"],
      ].forEach(([v, text]) => {
        const option = document.createElement("option");
        option.value = v;
        option.textContent = text;
        control.append(option);
      });
      if (el.spec[field.name] !== undefined)
        control.value = String(el.spec[field.name]);
    } else if (field.enum) {
      control = document.createElement("select");
      const blank = document.createElement("option");
      blank.value = "";
      blank.textContent = "default";
      control.append(blank);
      field.enum.forEach((value) => {
        const option = document.createElement("option");
        option.value = String(value);
        option.textContent = String(value);
        control.append(option);
      });
      if (el.spec[field.name] !== undefined)
        control.value = String(el.spec[field.name]);
    } else if (["object", "array", "elements", "any"].includes(field.kind)) {
      control = document.createElement("textarea");
      control.rows = 3;
      control.value =
        el.spec[field.name] === undefined
          ? ""
          : JSON.stringify(el.spec[field.name]);
      control.placeholder =
        field.kind === "elements"
          ? "JSON array of child elements"
          : "JSON value";
    } else {
      control = document.createElement("input");
      control.type = ["number", "integer"].includes(field.kind)
        ? "number"
        : "text";
      control.value = el.spec[field.name] ?? "";
      control.placeholder = el.spec[field.name] === undefined ? "default" : "";
    }
    control.dataset.key = field.name;
    row.append(control);
    fields.append(row);
  }
  fields.querySelectorAll("input,select,textarea").forEach(
    (control) =>
      (control.onchange = () => {
        try {
          let value = control.value;
          const field = (schema?.fields || []).find(
            (f) => f.name === control.dataset.key,
          );
          if (value === "") {
            if (field?.required)
              throw Error(`${control.dataset.key} is required`);
            if (el.spec[control.dataset.key] === undefined) return;
            checkpoint();
            delete el.spec[control.dataset.key];
          } else if (
            ["object", "array", "elements", "any"].includes(field?.kind)
          ) {
            value = JSON.parse(value);
            checkpoint();
            el.spec[control.dataset.key] = value;
          } else if (field?.kind === "boolean") {
            checkpoint();
            el.spec[control.dataset.key] = value === "true";
          } else if (
            ["number", "integer"].includes(field?.kind) &&
            !value.includes("{{") &&
            !value.includes("{%")
          ) {
            value = Number(value);
            if (
              !Number.isFinite(value) ||
              (field.kind === "integer" && !Number.isInteger(value))
            )
              throw Error(`${field.name} must be a ${field.kind}`);
            checkpoint();
            el.spec[control.dataset.key] = value;
          } else {
            checkpoint();
            el.spec[control.dataset.key] = value;
          }
          sync();
          render();
        } catch (error) {
          announce(error.message, true);
        }
      }),
  );
  root.append(fields);
  if (el.spec.type === "icon") {
    const label = document.createElement("label");
    label.className = "schema-field";
    label.innerHTML = `<span>${tr("Icon search")}</span>`;
    const input = document.createElement("input");
    input.setAttribute("list", "icon-options");
    input.value = el.spec.value || "";
    input.placeholder = "mdi:home";
    input.onchange = () => {
      checkpoint();
      el.spec.value = input.value;
      sync();
      render();
    };
    label.append(input);
    const list = document.createElement("datalist");
    list.id = "icon-options";
    Object.keys(icons).forEach((name) => {
      const option = document.createElement("option");
      option.value = name;
      list.append(option);
    });
    root.append(label, list);
  }
  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = tr("Advanced JSON");
  const area = document.createElement("textarea");
  area.className = "prop-editor";
  area.spellcheck = false;
  area.value = JSON.stringify(el.spec, null, 2);
  const apply = document.createElement("button");
  apply.type = "button";
  apply.textContent = tr("Apply properties");
  apply.className = "primary";
  apply.onclick = () => {
    try {
      const spec = JSON.parse(area.value);
      if (
        !spec ||
        typeof spec !== "object" ||
        Array.isArray(spec) ||
        !spec.type
      )
        throw Error("spec must be an object with a type");
      checkpoint();
      el.spec = spec;
      sync();
      render();
      announce("Properties applied");
    } catch (e) {
      announce(e.message, true);
    }
  };
  details.append(summary, area, apply);
  root.append(details);
}
function boardSize() {
  const board = $("board");
  board.style.width = `${profile.width * scale}px`;
  board.style.height = `${profile.height * scale}px`;
}
function drawOverlay() {
  const over = $("overlay");
  over.replaceChildren();
  doc.elements.forEach((el) => {
    const f = document.createElement("div");
    f.className = `frame${el.id === selected ? " selected" : ""}`;
    f.style.left = `${el.x * scale}px`;
    f.style.top = `${el.y * scale}px`;
    f.style.width = `${Math.max(1, el.width) * scale}px`;
    f.style.height = `${Math.max(1, el.height) * scale}px`;
    f.dataset.id = el.id;
    f.innerHTML = `<span class="name">${el.spec.type}</span>${el.id === selected ? '<i class="resize"></i>' : ""}`;
    f.onpointerdown = (e) => beginDrag(e, el);
    f.onclick = (e) => {
      e.stopPropagation();
      selected = el.id;
      drawOverlay();
      drawLayers();
      drawProperties();
    };
    over.append(f);
  });
}
function beginDrag(event, el) {
  if (event.button !== 0) return;
  event.preventDefault();
  selected = el.id;
  const resizing = event.target.classList.contains("resize");
  dragging = {
    id: el.id,
    resizing,
    startX: event.clientX,
    startY: event.clientY,
    orig: { x: el.x, y: el.y, width: el.width, height: el.height },
    snapshot: JSON.stringify(doc),
    changed: false,
  };
  $("overlay").setPointerCapture(event.pointerId);
  drawLayers();
  drawProperties();
}
$("overlay").onpointermove = (e) => {
  if (!dragging) return;
  const el = selectedElement();
  const dx = Math.round((e.clientX - dragging.startX) / scale),
    dy = Math.round((e.clientY - dragging.startY) / scale),
    o = dragging.orig;
  if (dragging.resizing) {
    el.width = Math.max(1, o.width + dx);
    el.height = Math.max(1, o.height + dy);
  } else {
    el.x = o.x + dx;
    el.y = o.y + dy;
  }
  dragging.changed ||= dx !== 0 || dy !== 0;
  drawOverlay();
};
$("overlay").onpointerup = () => {
  if (dragging?.changed) {
    undoStack.push(dragging.snapshot);
    if (undoStack.length > 100) undoStack.shift();
    redoStack = [];
    sync();
    render();
    buttons();
  }
  dragging = null;
};
$("overlay").onclick = () => {
  selected = null;
  drawOverlay();
  drawLayers();
  drawProperties();
};
async function render() {
  const request = ++renderSequence,
    snapshot = clone(doc);
  boardSize();
  drawOverlay();
  try {
    const result = await api("render", { document: snapshot, profile });
    if (request !== renderSequence) return false;
    $("preview").src = result.data_url;
    const warning = importWarnings.length
      ? ` · Import notes: ${importWarnings.join("; ")}`
      : "";
    announce(
      `Rendered ${profile.width} × ${profile.height} · ${snapshot.elements.length} elements${warning}`,
      false,
      importWarnings.length > 0,
    );
    return true;
  } catch (e) {
    if (request === renderSequence) {
      const warning = importWarnings.length
        ? ` · Import notes: ${importWarnings.join("; ")}`
        : "";
      announce(`${e.message}${warning}`, true);
    }
    return false;
  }
}
async function add(type) {
  try {
    const result = await api("newElement", { type });
    checkpoint();
    const el = result.element;
    el.id = crypto.randomUUID().replaceAll("-", "");
    el.x = Math.max(0, Math.round((profile.width - el.width) / 2));
    el.y = Math.max(0, Math.round((profile.height - el.height) / 2));
    doc.elements.push(el);
    selected = el.id;
    sync();
    await render();
  } catch (error) {
    announce(error.message, true);
  }
}
function undo() {
  if (!undoStack.length) return;
  redoStack.push(JSON.stringify(doc));
  doc = JSON.parse(undoStack.pop());
  sync();
  render();
  buttons();
}
function redo() {
  if (!redoStack.length) return;
  undoStack.push(JSON.stringify(doc));
  doc = JSON.parse(redoStack.pop());
  sync();
  render();
  buttons();
}
$("undo").onclick = undo;
$("redo").onclick = redo;
$("delete").onclick = () => {
  if (!selected) return;
  checkpoint();
  doc.elements = doc.elements.filter((e) => e.id !== selected);
  selected = doc.elements.at(-1)?.id || null;
  sync();
  render();
};
$("duplicate").onclick = () => {
  const e = selectedElement();
  if (!e) return;
  checkpoint();
  const c = clone(e);
  c.id = crypto.randomUUID().replaceAll("-", "");
  c.x += 8;
  c.y += 8;
  doc.elements.push(c);
  selected = c.id;
  sync();
  render();
};
function moveLayer(direction) {
  const i = doc.elements.findIndex((e) => e.id === selected);
  if (i < 0) return;
  const j = i + direction;
  if (j < 0 || j >= doc.elements.length) return;
  checkpoint();
  [doc.elements[i], doc.elements[j]] = [doc.elements[j], doc.elements[i]];
  sync();
  render();
}
$("raise").onclick = () => moveLayer(1);
$("lower").onclick = () => moveLayer(-1);
$("background").onchange = (e) => {
  checkpoint();
  doc.background = e.target.value;
  sync();
  render();
};
$("search").oninput = (e) => drawTypes(e.target.value);
$("apply-json").onclick = async () => {
  try {
    const next = JSON.parse($("json").value);
    await api("validate", { document: next, profile });
    checkpoint();
    if (await setDoc(next)) announce("Document updated");
  } catch (e) {
    announce(e.message, true);
  }
};
function openYaml(mode) {
  dialogMode = mode;
  $("dialog-title").textContent =
    mode === "import"
      ? tr("Import YAML")
      : mode === "payload"
        ? tr("Export imagespec YAML")
        : tr("Export design YAML");
  $("dialog-message").textContent = "";
  $("dialog-apply").hidden = mode !== "import";
  $("yaml").readOnly = mode !== "import";
  if (mode !== "import")
    api(mode === "payload" ? "dumpPayload" : "dumpYaml", {
      document: doc,
      profile,
    })
      .then((r) => ($("yaml").value = r.yaml))
      .catch((e) => announce(e.message, true));
  else $("yaml").value = "";
  $("yaml-dialog").showModal();
}
$("import").onclick = () => openYaml("import");
$("export").onclick = () => openYaml("export");
$("export-payload").onclick = () => openYaml("payload");
$("dialog-apply").onclick = async (e) => {
  e.preventDefault();
  try {
    const result = await api("parseYaml", { text: $("yaml").value, profile });
    checkpoint();
    importWarnings = result.issues || [];
    const rendered = await setDoc(result.document);
    $("yaml-dialog").close();
    if (rendered) {
      announce(
        importWarnings.join("; ") || "YAML imported",
        false,
        importWarnings.length > 0,
      );
    }
  } catch (error) {
    $("dialog-message").textContent = error.message;
  }
};
$("save").onclick = async () => {
  try {
    if (host.saveDocument) await host.saveDocument({ document: doc });
    else
      localStorage.setItem("imagespec-designer-document", JSON.stringify(doc));
    announce(tr("Saved"));
  } catch (e) {
    announce(e.message, true);
  }
};
async function loadTemplates() {
  templates = await api("templates");
  $("template-list").replaceChildren();
  templates.forEach((t) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = `${t.name} — ${t.description}`;
    b.onclick = () => {
      selectedTemplate = t;
      $("template-params").replaceChildren();
      Object.entries(t.parameters || {}).forEach(([name, p]) => {
        const l = document.createElement("label");
        l.className = "param";
        l.textContent = name;
        const input = document.createElement("input");
        input.value = p.default ?? "";
        input.dataset.param = name;
        l.append(input);
        $("template-params").append(l);
      });
    };
    $("template-list").append(b);
  });
}
$("templates").onclick = async () => {
  try {
    await loadTemplates();
    $("template-dialog").showModal();
  } catch (e) {
    announce(e.message, true);
  }
};
$("template-apply").onclick = async (e) => {
  e.preventDefault();
  if (!selectedTemplate) return;
  const values = Object.fromEntries(
    [...$("template-params").querySelectorAll("input")].map((i) => [
      i.dataset.param,
      i.value,
    ]),
  );
  try {
    const result = await api("applyTemplate", {
      id: selectedTemplate.id,
      values,
      profile,
    });
    checkpoint();
    const rendered = await setDoc(result.document);
    $("template-dialog").close();
    if (rendered) announce("Template loaded");
  } catch (err) {
    announce(err.message, true);
  }
};
window.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "z") {
    e.preventDefault();
    e.shiftKey ? redo() : undo();
  } else if ((e.metaKey || e.ctrlKey) && e.key === "y") {
    e.preventDefault();
    redo();
  } else if (
    (e.key === "Delete" || e.key === "Backspace") &&
    !["TEXTAREA", "INPUT"].includes(document.activeElement.tagName)
  )
    $("delete").click();
});
const designerApi = {
  getDocument() {
    return clone(doc);
  },
  async setDocument(next) {
    await api("validate", { document: next, profile });
    checkpoint();
    await setDoc(clone(next));
    return clone(doc);
  },
  async validate(next = doc) {
    return await api("validate", { document: next, profile });
  },
  async refresh() {
    await render();
    return clone(doc);
  },
};
window.imagespecDesigner = designerApi;
async function init() {
  document.title = host.title || "imagespec designer";
  $("brand").textContent = host.title || "imagespec designer";
  $("profile").textContent =
    `${profile.name} · ${profile.width} × ${profile.height} · ${profile.palette}`;
  const language = (host.language || navigator.language || "en").split("-")[0];
  try {
    const locale = await fetch(
      new URL(`locales/${language}.json`, import.meta.url),
    );
    if (locale.ok) localeMessages = await locale.json();
  } catch {}
  applyTranslations();
  try {
    const response = await fetch(new URL("icons.json", import.meta.url));
    if (response.ok) icons = await response.json();
  } catch {}
  const resp = await api("metadata");
  const packageVersion = host.packageVersion || resp.designer_version;
  $("version").textContent = packageVersion ? `v${packageVersion}` : "";
  $("version").title = packageVersion
    ? `imagespec-designer ${packageVersion}`
    : "";
  metadata = resp.elements || [];
  geometryMetadata = resp.geometry || {};
  starterTypes = resp.starters || [];
  drawTypes();
  if (host.loadDocument) {
    const result = await host.loadDocument();
    if (result?.document) doc = result.document;
  } else {
    try {
      const saved = localStorage.getItem("imagespec-designer-document");
      if (saved) doc = JSON.parse(saved);
    } catch {}
  }
  sync();
  await render();
}
init()
  .then(() => host.onReady?.(designerApi))
  .catch((e) => {
    announce(e.message, true);
    host.onError?.(e);
  });
