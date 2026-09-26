/* CNCguitarwizard in the browser: load Pyodide, install the package wheel,
   draw a form from the dataclass schema, run the build, offer downloads. */

const PYODIDE_INDEX = "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/";

const status = document.getElementById("status");
const form = document.getElementById("form");
const buildButton = document.getElementById("build");
const resetButton = document.getElementById("reset");
const errorBox = document.getElementById("error");
const progress = document.getElementById("progress");
const progressFill = progress.querySelector(".fill");
const progressLabel = progress.querySelector(".label");
const output = document.getElementById("output");
const intro = document.getElementById("intro");
const showAdvanced = document.getElementById("show-advanced");

let pyodide = null;
let schema = null;
let blobUrls = [];

function setStatus(text, kind) {
  status.textContent = text;
  status.className = kind || "";
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

function clearError() {
  errorBox.classList.add("hidden");
  errorBox.textContent = "";
}

async function boot() {
  try {
    pyodide = await loadPyodide({ indexURL: PYODIDE_INDEX });
    setStatus("Installing cncguitarwizard…");
    await pyodide.loadPackage("micropip");
    const manifest = window.CNCGW_MANIFEST
      || await (await fetch("wheel.json", { cache: "no-store" })).json();
    const micropip = pyodide.pyimport("micropip");
    const wheelUrl = new URL("wheels/" + manifest.wheel, location.href);
    wheelUrl.searchParams.set("v", manifest.build || String(Date.now()));
    await micropip.install(wheelUrl.href);
    const schemaJson = await pyodide.runPythonAsync(
      "import json\nfrom cncguitarwizard.webapp import parameter_schema\njson.dumps(parameter_schema())"
    );
    schema = JSON.parse(schemaJson);
    renderForm();
    buildButton.disabled = false;
    resetButton.disabled = false;
    setStatus(`Ready — ${manifest.wheel} (build ${manifest.build || "dev"})`, "ok");
  } catch (error) {
    console.error(error);
    setStatus("Failed to start", "bad");
    showError("The Python runtime could not be started:\n" + error);
  }
}

function renderForm() {
  form.innerHTML = "";
  const sections = [
    ["prototype", schema.prototype],
    ["machining", schema.machining],
  ];
  for (const [set, groups] of sections) {
    for (const group of groups) {
      const details = document.createElement("details");
      if (group.title === "Body" || group.title === "Machining") details.open = true;
      const summary = document.createElement("summary");
      summary.textContent = group.title;
      details.appendChild(summary);
      const holder = document.createElement("div");
      holder.className = "fields";
      renderFieldList(set, group.fields, holder);
      details.appendChild(holder);
      form.appendChild(details);
    }
  }
  applyAdvancedToggle();
}

// Basic fields first; the rarely changed ones fold away behind
// "Advanced", whose summary lights up when one of them has been edited.
function renderFieldList(set, fields, holder) {
  const advanced = [];
  for (const field of fields) {
    if (field.advanced) advanced.push(field);
    else holder.appendChild(renderField(set, field));
  }
  if (advanced.length === 0) return;
  const details = document.createElement("details");
  details.className = "advanced";
  details.open = showAdvanced.checked;
  const summary = document.createElement("summary");
  summary.textContent = `Advanced (${advanced.length})`;
  details.appendChild(summary);
  const inner = document.createElement("div");
  inner.className = "fields";
  for (const field of advanced) inner.appendChild(renderField(set, field));
  details.appendChild(inner);
  details.addEventListener("input", () => flagAdvancedSummary(details));
  details.addEventListener("change", () => flagAdvancedSummary(details));
  holder.appendChild(details);
}

function flagAdvancedSummary(details) {
  const summary = details.querySelector(":scope > summary");
  summary.classList.toggle("changed", details.querySelector(".changed") !== null);
}

function applyAdvancedToggle() {
  for (const details of form.querySelectorAll("details.advanced")) {
    details.open = showAdvanced.checked;
  }
}

function renderField(set, field) {
  if (field.type === "variant") return renderVariantField(set, field);
  if (field.type === "choice") return renderChoiceField(set, field);
  const row = document.createElement("div");
  row.className = "field";
  const label = document.createElement("label");
  label.textContent = field.name;
  label.htmlFor = set + "." + field.name;
  const input = document.createElement("input");
  input.id = set + "." + field.name;
  input.dataset.set = set;
  input.dataset.name = field.name;
  input.dataset.type = field.type;
  input.dataset.default = JSON.stringify(field.default);
  const initial = "value" in field ? field.value : field.default;
  if (field.type === "bool") {
    input.type = "checkbox";
    input.checked = Boolean(initial);
  } else if (field.type === "float" || field.type === "int") {
    input.type = "number";
    input.step = field.type === "int" ? "1" : "any";
    input.value = String(initial);
  } else {
    input.type = "text";
    input.value = field.type === "optional_float" && initial === null
      ? ""
      : JSON.stringify(initial);
  }
  input.addEventListener("input", () => markChanged(input));
  row.appendChild(label);
  row.appendChild(input);
  return row;
}

function renderChoiceField(set, field) {
  const row = document.createElement("div");
  row.className = "field";
  const label = document.createElement("label");
  label.textContent = field.name;
  label.htmlFor = set + "." + field.name;
  const select = document.createElement("select");
  select.id = label.htmlFor;
  select.className = "choice";
  select.dataset.set = set;
  select.dataset.name = field.name;
  select.dataset.default = JSON.stringify(field.default);
  const initial = "value" in field ? field.value : field.default;
  for (const option of field.options) {
    const element = document.createElement("option");
    element.value = option;
    element.textContent = option;
    element.selected = option === initial;
    select.appendChild(element);
  }
  select.addEventListener("change", () => {
    select.classList.toggle("changed", JSON.stringify(select.value) !== select.dataset.default);
  });
  row.appendChild(label);
  row.appendChild(select);
  return row;
}

function renderVariantField(set, field) {
  // A dropdown of kinds; the chosen kind's own fields appear beneath it.
  const holder = document.createElement("div");
  holder.className = "variant";
  holder.dataset.set = set;
  holder.dataset.name = field.name;
  holder.dataset.defaultKind = field.default.kind;
  const row = document.createElement("div");
  row.className = "field";
  const label = document.createElement("label");
  label.textContent = field.name;
  label.htmlFor = set + "." + field.name + ".kind";
  const select = document.createElement("select");
  select.id = label.htmlFor;
  select.className = "kind";
  for (const [kind, variant] of Object.entries(field.variants)) {
    const option = document.createElement("option");
    option.value = kind;
    option.textContent = variant.label;
    option.selected = kind === field.default.kind;
    select.appendChild(option);
  }
  row.appendChild(label);
  row.appendChild(select);
  holder.appendChild(row);
  const sub = document.createElement("div");
  sub.className = "subfields";
  holder.appendChild(sub);

  const renderSubfields = (kind, values) => {
    sub.innerHTML = "";
    const subfields = field.variants[kind].fields.map((subfield) => (
      values && subfield.name in values
        ? { ...subfield, default: subfield.default, value: values[subfield.name] }
        : subfield
    ));
    renderFieldList(set + "." + field.name, subfields, sub);
    select.classList.toggle("changed", kind !== field.default.kind);
    if (field.name === "body_shape") bodyEditor.sync(kind, sub);
  };
  renderSubfields(field.default.kind, field.default);
  select.addEventListener("change", () => renderSubfields(select.value, null));
  return holder;
}

function markChanged(input) {
  const current = JSON.stringify(readValue(input));
  input.classList.toggle("changed", current !== input.dataset.default);
}

function readValue(input) {
  const type = input.dataset.type;
  if (type === "bool") return input.checked;
  if (type === "int") return parseInt(input.value, 10);
  if (type === "float") return parseFloat(input.value);
  if (type === "optional_float") {
    return input.value.trim() === "" ? null : parseFloat(input.value);
  }
  return JSON.parse(input.value);
}

function collectValues() {
  const payload = { prototype: {}, machining: {} };
  const assign = (set, name, value) => {
    // "prototype.body_bridge" addresses a variant's sub-object.
    const parts = set.split(".");
    let target = payload[parts[0]];
    for (const part of parts.slice(1)) {
      target[part] = target[part] || {};
      target = target[part];
    }
    target[name] = value;
  };
  for (const variant of form.querySelectorAll(".variant")) {
    assign(variant.dataset.set, variant.dataset.name, {
      kind: variant.querySelector("select.kind").value,
    });
  }
  for (const select of form.querySelectorAll("select.choice")) {
    assign(select.dataset.set, select.dataset.name, select.value);
  }
  for (const input of form.querySelectorAll("input")) {
    let value;
    try {
      value = readValue(input);
    } catch (error) {
      throw new Error(`${input.dataset.name}: not valid JSON (${error.message})`);
    }
    if (typeof value === "number" && Number.isNaN(value)) {
      throw new Error(`${input.dataset.name}: not a number`);
    }
    assign(input.dataset.set, input.dataset.name, value);
  }
  return payload;
}

// Let the browser paint between Python stages (Pyodide blocks the page
// thread while a stage runs).
function paint() {
  return new Promise((resolve) => requestAnimationFrame(() => setTimeout(resolve, 0)));
}

function showProgress(completed, total, label) {
  progress.classList.remove("hidden");
  progressFill.style.width = `${Math.round((100 * completed) / total)}%`;
  progressLabel.textContent = label
    ? `${completed + 1}/${total} · ${label}`
    : `${completed}/${total} · done`;
}

async function runPython(code) {
  return JSON.parse(await pyodide.runPythonAsync(code));
}

async function build() {
  clearError();
  let payload;
  try {
    payload = collectValues();
  } catch (error) {
    showError(error.message);
    return;
  }
  buildButton.disabled = true;
  buildButton.classList.add("busy");
  buildButton.textContent = "Building…";
  setStatus("Building…");
  const started = performance.now();
  try {
    pyodide.globals.set("payload_json", JSON.stringify(payload));
    const startResult = await runPython(
      "import json\nfrom cncguitarwizard.webapp import start_build\n" +
      "json.dumps(start_build(json.loads(payload_json)))"
    );
    if (startResult.error) {
      showError(startResult.error);
      setStatus("Parameters rejected", "bad");
      return;
    }
    const stages = startResult.stages;
    showProgress(0, stages.length, stages[0]);
    await paint();
    for (;;) {
      const step = await runPython(
        "import json\nfrom cncguitarwizard.webapp import advance_build\n" +
        "json.dumps(advance_build())"
      );
      if (step.error) {
        showError(step.error);
        setStatus("Build failed", "bad");
        return;
      }
      showProgress(step.completed, step.total, step.next);
      await paint();
      if (step.done) break;
    }
    const result = await runPython(
      "import json\nfrom cncguitarwizard.webapp import finish_build\n" +
      "json.dumps(finish_build())"
    );
    if (result.error) {
      showError(result.error);
      setStatus("Build failed", "bad");
      return;
    }
    showResult(result);
    const seconds = ((performance.now() - started) / 1000).toFixed(1);
    setStatus(`Built in ${seconds} s`, "ok");
  } catch (error) {
    console.error(error);
    showError("Build failed:\n" + error);
    setStatus("Build failed", "bad");
  } finally {
    buildButton.disabled = false;
    buildButton.classList.remove("busy");
    buildButton.textContent = "Build Prototype001";
    setTimeout(() => progress.classList.add("hidden"), 1500);
  }
}

function showResult(result) {
  for (const url of blobUrls) URL.revokeObjectURL(url);
  blobUrls = [];
  intro.classList.add("hidden");
  output.classList.remove("hidden");

  document.getElementById("plan").innerHTML = result.plan_view;

  const tabs = document.getElementById("tabs");
  const toolpath = document.getElementById("toolpath");
  tabs.innerHTML = "";
  toolpath.innerHTML = "";
  const previews = Object.keys(result.files).filter((name) => name.endsWith(".svg"));
  previews.forEach((name, index) => {
    const button = document.createElement("button");
    button.textContent = name.replace(".svg", "");
    button.addEventListener("click", () => {
      for (const other of tabs.children) other.classList.remove("active");
      button.classList.add("active");
      toolpath.innerHTML = result.files[name];
    });
    tabs.appendChild(button);
    if (name === "Body_top.svg" || (previews.length === 1 && index === 0)) button.click();
  });

  const files = document.getElementById("files");
  files.innerHTML = "<tr><th>File</th><th>Size</th><th></th></tr>";
  const order = Object.keys(result.report.gcode);
  const rank = (name) => {
    if (name.startsWith("Prototype001")) return 0;
    const stem = name.replace(/\.(nc|svg)$/, "");
    const index = order.indexOf(stem);
    if (index >= 0) return 10 + index * 2 + (name.endsWith(".svg") ? 1 : 0);
    return 1000;
  };
  const names = Object.keys(result.files).sort((a, b) => rank(a) - rank(b));
  for (const name of names) {
    const text = result.files[name];
    const type = name.endsWith(".svg") ? "image/svg+xml"
      : name.endsWith(".json") ? "application/json" : "text/plain";
    const url = URL.createObjectURL(new Blob([text], { type }));
    blobUrls.push(url);
    const row = document.createElement("tr");
    row.innerHTML =
      `<td>${name}</td><td>${(text.length / 1024).toFixed(0)} kB</td>` +
      `<td><a class="download" href="${url}" download="${name}">Download</a></td>`;
    if (name.endsWith(".nc")) {
      const button = document.createElement("button");
      button.className = "simulate";
      button.textContent = "Simulate";
      button.title = "Copy this program to the clipboard and open NC Viewer below";
      button.addEventListener("click", () => simulate(name, text));
      row.lastElementChild.appendChild(button);
    }
    files.appendChild(row);
  }

  const summary = document.getElementById("summary");
  const report = result.report;
  const rows = [];
  for (const [part, stock] of Object.entries(report.stock)) {
    rows.push([`${part} blank`, `${stock.length_mm} × ${stock.width_mm} × ${stock.thickness_mm} mm, pins at machine X ${stock.index_pins_machine_xy.map((p) => p[0]).join(" / ")}`]);
  }
  for (const [name, info] of Object.entries(report.gcode)) {
    rows.push([name, `${info.tool}: ${info.estimated_minutes} min, ${(info.cutting_length_mm / 1000).toFixed(1)} m of cutting, ${info.operations.length} operations`]);
  }
  rows.push(["Version", report.version]);
  summary.innerHTML = rows.map(([k, v]) => `<tr><th>${k}</th><td>${v}</td></tr>`).join("");
}

// NC Viewer (ncviewer.com) has no URL or postMessage way to receive a
// program, so the button copies it to the clipboard and opens the viewer
// in an iframe; the user pastes into its editor.
const SIMULATOR_URL = "https://ncviewer.com/";

function simulatorPanel() {
  // A browser that kept an older index.html cached (Safari does) has no
  // panel markup; build it after the downloads table in that case.
  let panel = document.getElementById("simulator");
  if (!panel) {
    panel = document.createElement("div");
    panel.id = "simulator";
    panel.className = "simulator hidden";
    panel.innerHTML =
      '<h2>Simulator <span id="simulator-file" class="note"></span></h2>' +
      '<p id="simulator-hint" class="note"></p>' +
      '<iframe id="simulator-frame" title="NC Viewer G-code simulator" ' +
      'allow="clipboard-read; clipboard-write" ' +
      'style="width:100%;height:640px;border:1px solid #d9cfbd;border-radius:6px;background:#fff"></iframe>';
    const files = document.getElementById("files");
    files.parentNode.insertBefore(panel, files.nextSibling);
  }
  return panel;
}

async function simulate(name, text) {
  const panel = simulatorPanel();
  const frame = document.getElementById("simulator-frame");
  const hint = document.getElementById("simulator-hint");
  document.getElementById("simulator-file").textContent = `— ${name}`;
  panel.classList.remove("hidden");
  if (!frame.src) frame.src = SIMULATOR_URL;
  let copied = false;
  try {
    await navigator.clipboard.writeText(text);
    copied = true;
  } catch (error) {
    console.warn("Clipboard write failed", error);
  }
  hint.className = copied ? "note ok" : "note bad";
  hint.textContent = copied
    ? `${name} is on the clipboard: click into the NC Viewer editor below and paste (Ctrl/Cmd+V), or drop the downloaded file onto it.`
    : `Could not copy to the clipboard: download ${name} and drop it onto NC Viewer below, or open it there with its file button.`;
  panel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function reset() {
  renderForm();
  clearError();
}

// ---------------------------------------------------------------------------
// "Your design" body editor: drag the outline's control points over the
// fixed features (neck, pocket, routes, cavities), which Python lays out.
// The outline is the same closed Catmull-Rom spline Python builds, and the
// points are written back to the body_shape.control_points field as JSON.

const SVG_NS = "http://www.w3.org/2000/svg";

function closedCatmullRom(points, samples) {
  const out = [];
  const n = points.length;
  const blend = (a, b, c, d, t) => 0.5 * (
    2 * b + (c - a) * t + (2 * a - 5 * b + 4 * c - d) * t * t
    + (3 * b - a - 3 * c + d) * t * t * t
  );
  for (let i = 0; i < n; i++) {
    const p0 = points[(i - 1 + n) % n], p1 = points[i];
    const p2 = points[(i + 1) % n], p3 = points[(i + 2) % n];
    for (let s = 0; s < samples; s++) {
      const t = s / samples;
      out.push([blend(p0[0], p1[0], p2[0], p3[0], t), blend(p0[1], p1[1], p2[1], p3[1], t)]);
    }
  }
  return out;
}

function pointInPolygon(x, y, polygon) {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i], [xj, yj] = polygon[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

const bodyEditor = {
  panel: document.getElementById("body-editor"),
  svg: document.getElementById("body-editor-svg"),
  status: document.getElementById("body-editor-status"),
  size: document.getElementById("body-editor-size"),
  input: null,      // the control_points text field
  points: [],       // [[x, y], ...] relative to the heel end
  layout: null,     // Python's fixed features
  outlinePath: null,
  handles: [],
  refreshTimer: null,

  sync(kind, subfields) {
    this.input = subfields.querySelector("input[data-name='control_points']");
    const active = kind === "your_design" && this.input !== null;
    this.panel.classList.toggle("hidden", !active);
    if (!active) return;
    try {
      this.points = JSON.parse(this.input.value);
    } catch (error) {
      this.points = [];
    }
    this.refresh();
  },

  async refresh() {
    if (this.panel.classList.contains("hidden") || !pyodide) return;
    let payload;
    try {
      payload = collectValues();
    } catch (error) {
      this.setStatus(`Cannot place the features: ${error.message}`, "bad");
      return;
    }
    pyodide.globals.set("payload_json", JSON.stringify(payload));
    const layout = await runPython(
      "import json\nfrom cncguitarwizard.webapp import body_editor_layout\n" +
      "json.dumps(body_editor_layout(json.loads(payload_json)))"
    );
    if (layout.error) {
      this.setStatus(layout.error, "bad");
      return;
    }
    this.layout = layout;
    if (this.points.length < 4) this.points = layout.start_points.map((p) => [...p]);
    this.draw();
  },

  scheduleRefresh() {
    clearTimeout(this.refreshTimer);
    this.refreshTimer = setTimeout(() => this.refresh(), 400);
  },

  element(name, attributes, parent) {
    const node = document.createElementNS(SVG_NS, name);
    for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
    (parent || this.svg).appendChild(node);
    return node;
  },

  pathData(points) {
    return points.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(2)},${(-y).toFixed(2)}`).join(" ") + " Z";
  },

  outline() {
    return closedCatmullRom(this.points, this.layout.samples_per_segment);
  },

  draw() {
    const layout = this.layout;
    this.svg.innerHTML = "";
    // Frame everything: the outline plus the features on the body.
    const bodyFeatures = layout.polygons.filter((p) => p.role !== "neck");
    const all = [...this.outline(), ...bodyFeatures.flatMap((p) => p.points)];
    const xs = all.map((p) => p[0]), ys = all.map((p) => p[1]);
    const margin = 40;
    const minX = Math.min(...xs) - margin, maxX = Math.max(...xs) + margin;
    const minY = Math.min(...ys) - margin, maxY = Math.max(...ys) + margin;
    this.svg.setAttribute("viewBox", `${minX} ${-maxY} ${maxX - minX} ${maxY - minY}`);

    const grid = this.element("g", { stroke: "#eee6d8", "stroke-width": 0.5 });
    for (let x = Math.ceil(minX / 50) * 50; x <= maxX; x += 50) {
      this.element("line", { x1: x, y1: -maxY, x2: x, y2: -minY }, grid);
    }
    for (let y = Math.ceil(minY / 50) * 50; y <= maxY; y += 50) {
      this.element("line", { x1: minX, y1: -y, x2: maxX, y2: -y }, grid);
    }
    this.element("line", { x1: minX, y1: 0, x2: maxX, y2: 0, stroke: "#bbb", "stroke-width": 0.5, "stroke-dasharray": "4,3" });

    this.outlinePath = this.element("path", { class: "outline", d: this.pathData(this.outline()) });
    this.outlinePath.addEventListener("dblclick", (event) => this.addPoint(event));

    const styles = {
      neck: { fill: "#3b2a1a", "fill-opacity": 0.85, stroke: "none" },
      pocket: { fill: "#f2c4b3", "fill-opacity": 0.9, stroke: "#7a3a1a", "stroke-width": 0.5 },
      pickup: { fill: "#f2c4b3", stroke: "#7a3a1a", "stroke-width": 0.5 },
      bridge: { fill: "#f2c4b3", stroke: "#7a3a1a", "stroke-width": 0.5 },
      cover: { fill: "#c9b7e6", "fill-opacity": 0.35, stroke: "#5a3a8a", "stroke-width": 0.5, "stroke-dasharray": "3,2" },
      rear: { fill: "#c9b7e6", "fill-opacity": 0.55, stroke: "#5a3a8a", "stroke-width": 0.6, "stroke-dasharray": "3,2" },
    };
    // Features with a group can be dragged; the rest (neck, pocket,
    // bridge) follow the neck and scale and stay put.
    const features = this.element("g", {});
    const place = (node, group, name) => {
      if (group) {
        node.setAttribute("data-group", group);
        node.classList.add("movable");
        node.addEventListener("pointerdown", (event) => this.startMove(event, group, node));
      } else {
        node.setAttribute("pointer-events", "none");
      }
      this.element("title", {}, node).textContent = group ? `${name} — drag to move` : name;
    };
    for (const polygon of layout.polygons) {
      const node = this.element("path", { d: this.pathData(polygon.points), ...styles[polygon.role] }, features);
      place(node, polygon.group, polygon.name);
    }
    for (const circle of layout.circles) {
      const node = this.element("circle", { cx: circle.x, cy: -circle.y, r: circle.r, fill: "#fff", stroke: "#222", "stroke-width": 0.5 }, features);
      place(node, circle.group, circle.name);
    }
    const jack = layout.jack;
    const bore = this.element("line", { x1: jack.x, y1: -jack.y, x2: jack.x2, y2: -jack.y2, stroke: "#222", "stroke-width": jack.r * 2, "stroke-opacity": 0.25 }, features);
    place(bore, jack.group, "Output jack");
    const socket = this.element("circle", { cx: jack.x, cy: -jack.y, r: jack.r, fill: "#fff", "fill-opacity": 0.6, stroke: "#222", "stroke-width": 0.8 }, features);
    place(socket, jack.group, "Output jack");

    this.handles = this.points.map((point, index) => {
      const handle = this.element("circle", { class: "handle", cx: point[0], cy: -point[1], r: 4 });
      handle.addEventListener("pointerdown", (event) => this.startDrag(event, index, handle));
      handle.addEventListener("contextmenu", (event) => { event.preventDefault(); this.removePoint(index); });
      return handle;
    });
    this.check();
  },

  toModel(event) {
    const point = this.svg.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    const local = point.matrixTransform(this.svg.getScreenCTM().inverse());
    return [Math.round(local.x * 10) / 10, Math.round(-local.y * 10) / 10];
  },

  startDrag(event, index, handle) {
    if (event.altKey) {
      this.removePoint(index);
      return;
    }
    event.preventDefault();
    handle.classList.add("dragging");
    const move = (moveEvent) => {
      this.points[index] = this.toModel(moveEvent);
      handle.setAttribute("cx", this.points[index][0]);
      handle.setAttribute("cy", -this.points[index][1]);
      this.outlinePath.setAttribute("d", this.pathData(this.outline()));
      this.check();
    };
    const end = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", end);
      window.removeEventListener("pointercancel", end);
      handle.classList.remove("dragging");
      this.commit();
      this.draw();
    };
    // Listen on the window so a fast drag that outruns the handle still
    // follows the pointer.
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
  },

  // Drag a feature group; on drop, move the form fields that place it and
  // let Python lay the features out again. Pickups slide along the neck
  // only; moving the control cavity carries its pots with it.
  startMove(event, group, node) {
    event.preventDefault();
    event.stopPropagation();
    const start = this.toModel(event);
    const members = [...this.svg.querySelectorAll(`[data-group="${group}"]`)];
    if (group === "control") members.push(...this.svg.querySelectorAll('[data-group^="pot:"]'));
    const alongNeck = group.startsWith("pickup:");
    let delta = [0, 0];
    const move = (moveEvent) => {
      const [x, y] = this.toModel(moveEvent);
      delta = [x - start[0], alongNeck ? 0 : y - start[1]];
      for (const member of members) member.setAttribute("transform", `translate(${delta[0]} ${-delta[1]})`);
    };
    const end = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", end);
      window.removeEventListener("pointercancel", end);
      if (delta[0] || delta[1]) {
        this.applyMove(group, delta);
        this.refresh();
      } else {
        for (const member of members) member.removeAttribute("transform");
      }
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
  },

  field(set, name) {
    return form.querySelector(`[data-set="${set}"][data-name="${name}"]`);
  },

  setField(input, value) {
    if (!input) return;
    input.value = input.dataset.type === "json" ? JSON.stringify(value) : String(value);
    markChanged(input);
    const fold = input.closest("details.advanced");
    if (fold) flagAdvancedSummary(fold);
  },

  shiftField(set, name, amount) {
    const input = this.field(set, name);
    if (input) this.setField(input, Math.round((readValue(input) + amount) * 10) / 10);
  },

  applyMove(group, [dx, dy]) {
    const shape = "prototype.body_shape";
    const round = (value) => Math.round(value * 10) / 10;
    const movePots = (predicate) => {
      const input = this.field(shape, "pot_offsets");
      const pots = readValue(input).map(([x, y], index) => (
        predicate(index) ? [round(x + dx), round(y + dy)] : [x, y]
      ));
      this.setField(input, pots);
    };
    if (group === "control") {
      const input = this.field(shape, "control_shift");
      const [sx, sy] = readValue(input);
      this.setField(input, [round(sx + dx), round(sy + dy)]);
      movePots(() => true);
    } else if (group === "switch") {
      for (const name of ["switch_cavity_offset", "switch_cover_offset"]) this.shiftField(shape, name, dx);
      for (const name of ["switch_cavity_y", "switch_cover_y"]) this.shiftField(shape, name, dy);
    } else if (group.startsWith("pot:")) {
      const target = Number(group.split(":")[1]);
      movePots((index) => index === target);
    } else if (group === "jack") {
      this.shiftField(shape, "jack_offset", dx);
      this.shiftField(shape, "jack_y", dy);
    } else if (group === "pickup:neck") {
      this.shiftField("prototype", "body_neck_pickup_offset", dx);
    } else if (group === "pickup:bridge") {
      // The offset is measured ahead of the scale line, toward the nut.
      // Start from where the route really is: a bridge that reaches ahead
      // of the scale line (a Floyd Rose) pushes it further forward than
      // the field alone says.
      const route = this.layout.polygons.find((p) => p.group === "pickup:bridge");
      const xs = route.points.map((p) => p[0]);
      const centre = (Math.min(...xs) + Math.max(...xs)) / 2;
      const scale = readValue(this.field("prototype", "scale_length")) - this.layout.heel_end;
      this.setField(this.field("prototype", "body_bridge_pickup_offset"), round(scale - (centre + dx)));
    }
  },

  addPoint(event) {
    const [x, y] = this.toModel(event);
    // Insert after the control point whose segment passes nearest the click.
    const samples = this.layout.samples_per_segment;
    const outline = this.outline();
    let best = 0, bestDistance = Infinity;
    outline.forEach(([ox, oy], i) => {
      const distance = (ox - x) ** 2 + (oy - y) ** 2;
      if (distance < bestDistance) { bestDistance = distance; best = i; }
    });
    this.points.splice(Math.floor(best / samples) + 1, 0, [x, y]);
    this.commit();
    this.draw();
  },

  removePoint(index) {
    if (this.points.length <= 4) {
      this.setStatus("The outline needs at least four handles.", "bad");
      return;
    }
    this.points.splice(index, 1);
    this.commit();
    this.draw();
  },

  reset() {
    if (!this.layout) return;
    this.points = this.layout.start_points.map((p) => [...p]);
    this.commit();
    this.draw();
  },

  commit() {
    this.input.value = JSON.stringify(this.points);
    markChanged(this.input);
    const fold = this.input.closest("details.advanced");
    if (fold) flagAdvancedSummary(fold);
  },

  // Report features left outside the outline and the body's size.
  check() {
    const outline = this.outline();
    const xs = outline.map((p) => p[0]), ys = outline.map((p) => p[1]);
    this.size.textContent = `— ${(Math.max(...xs) - Math.min(...xs)).toFixed(0)} × ${(Math.max(...ys) - Math.min(...ys)).toFixed(0)} mm`;
    const outside = new Set();
    for (const polygon of this.layout.polygons) {
      if (polygon.role === "neck") continue;
      // The pocket opens onto the horn gap: only its tail wall must be in wood.
      const points = polygon.role === "pocket" ? polygon.points.filter((p) => p[0] > -1) : polygon.points;
      if (points.some(([x, y]) => !pointInPolygon(x, y, outline))) outside.add(polygon.name);
    }
    for (const circle of this.layout.circles) {
      if (!pointInPolygon(circle.x, circle.y, outline)) outside.add(circle.name);
    }
    if (outside.size) {
      this.setStatus(`Outside the outline: ${[...outside].join(", ")}.`, "bad");
    } else {
      this.setStatus("Every feature fits inside the outline.", "ok");
    }
  },

  setStatus(text, kind) {
    this.status.textContent = text;
    this.status.className = `note ${kind}`;
  },
};

document.getElementById("body-editor-reset").addEventListener("click", () => bodyEditor.reset());
form.addEventListener("input", (event) => {
  if (event.target.dataset.name !== "control_points") {
    bodyEditor.scheduleRefresh();
    return;
  }
  // Points typed into the JSON field redraw the editor when they parse.
  try {
    const points = JSON.parse(event.target.value);
    if (Array.isArray(points) && points.length >= 4 && bodyEditor.layout) {
      bodyEditor.points = points;
      bodyEditor.draw();
    }
  } catch (error) {
    // Keep the last good drawing while the text is being edited.
  }
});
form.addEventListener("change", (event) => {
  if (event.target.dataset.name !== "control_points") bodyEditor.scheduleRefresh();
});

buildButton.addEventListener("click", build);
resetButton.addEventListener("click", reset);
showAdvanced.addEventListener("change", applyAdvancedToggle);
boot();
