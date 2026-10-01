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
const instrumentSelect = document.getElementById("instrument");
const saveDesignButton = document.getElementById("save-design");
const loadDesignButton = document.getElementById("load-design");
const loadDesignFile = document.getElementById("load-design-file");

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
    for (const [key, instrument] of Object.entries(schema.instruments)) {
      const option = document.createElement("option");
      option.value = key;
      option.textContent = instrument.label;
      instrumentSelect.appendChild(option);
    }
    instrumentSelect.dataset.current = instrumentSelect.value;
    renderForm();
    buildButton.disabled = false;
    resetButton.disabled = false;
    saveDesignButton.disabled = false;
    loadDesignButton.disabled = false;
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
    for (let group of groups) {
      // The chosen instrument's defaults replace the electric guitar's.
      const overrides = set === "prototype"
        ? schema.instruments[instrumentSelect.value].overrides
        : {};
      group = {
        ...group,
        fields: group.fields.map((field) => (
          field.name in overrides ? { ...field, default: overrides[field.name] } : field
        )),
      };
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
  applyStringLimits();
  setTimeout(() => headstockEditor.sync(), 0);
}

// Hide the kinds drawn for fewer strings than the instrument has (the
// Kahler, Floyd Rose and Tune-o-matic on a seven- or eight-string); if one
// of them is chosen, switch to the first kind that fits.
function applyStringLimits() {
  const countInput = form.querySelector('[data-set="prototype"][data-name="string_count"]');
  const count = countInput ? readValue(countInput) : 6;
  for (const holder of form.querySelectorAll(".variant")) {
    const field = variantFields[holder.dataset.name];
    if (!field) continue;
    const select = holder.querySelector("select.kind");
    for (const option of select.options) {
      const limit = field.variants[option.value].max_strings;
      const unfit = limit != null && count > limit;
      option.hidden = unfit;
      option.disabled = unfit;
    }
    if (select.selectedOptions[0]?.disabled) {
      const fitting = [...select.options].find((option) => !option.disabled);
      if (fitting) {
        select.value = fitting.value;
        select.dispatchEvent(new Event("change"));
      }
    }
    // A hardtail has a hole per string: keep its count with the instrument's.
    const holes = holder.querySelector(`[data-set="prototype.${holder.dataset.name}"][data-name="string_count"]`);
    if (holes && readValue(holes) !== count) {
      holes.value = String(count);
      markChanged(holes);
    }
  }
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
    element.textContent = field.labels?.[option] ?? option;
    element.selected = option === initial;
    select.appendChild(element);
  }
  select.addEventListener("change", () => {
    select.classList.toggle("changed", JSON.stringify(select.value) !== select.dataset.default);
    if (field.name === "locking_nut") fitNutWidth(select.value);
  });
  row.appendChild(label);
  row.appendChild(select);
  return row;
}

// A locking nut needs a neck at least as wide as itself at the nut: on
// choosing one, widen nut_width to it (to the next half millimetre).
function fitNutWidth(kind) {
  const width = schema.locking_nut_widths?.[kind];
  const input = form.querySelector('[data-set="prototype"][data-name="nut_width"]');
  if (!width || !input || readValue(input) >= width) return;
  setControlValue(input, Math.ceil(width * 2) / 2);
}

const variantFields = {};

function renderVariantField(set, field) {
  // A dropdown of kinds; the chosen kind's own fields appear beneath it.
  variantFields[field.name] = field;
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
  // With a single kind (the body, always drawn) there is nothing to choose.
  row.hidden = Object.keys(field.variants).length < 2;
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
  const payload = { prototype: { instrument: instrumentSelect.value }, machining: {} };
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

  // One list per part (body, neck, fretboard, covers), each program
  // numbered in the order it is run, its toolpath plot beneath it; the
  // model scripts and the report come first.
  const files = document.getElementById("files");
  files.innerHTML = "";
  const gcode = result.report.gcode;
  const isProgram = (name) => /\.k?nc$/.test(name);
  const stemOf = (name) => name.replace(/\.(nc|knc|svg)$/, "");
  const programOf = (name) => (/\.(nc|knc|svg)$/.test(name) ? gcode[stemOf(name)] : undefined);
  // build.json lists the programs alphabetically: order by part, then step.
  const partOrder = ["Model and report", "Body", "Neck", "Fretboard", "Covers"];
  const groups = new Map(partOrder.map((part) => [part, []]));
  for (const info of Object.values(gcode)) if (!groups.has(info.part)) groups.set(info.part, []);
  for (const name of Object.keys(result.files)) {
    const info = programOf(name);
    groups.get(info ? info.part : "Model and report").push(name);
  }
  const rank = (name) => {
    const info = programOf(name);
    return info ? info.step * 2 + (name.endsWith(".svg") ? 1 : 0) : 0;
  };
  const titles = {
    Body: "Body — top face up first, then flipped onto the dowels",
    Neck: "Neck",
    Fretboard: "Fretboard",
    Covers: "Covers — cut from sheet, in any order",
  };
  for (const [part, members] of groups) {
    if (!members.length) continue;
    const heading = document.createElement("tr");
    heading.className = "file-group";
    heading.innerHTML = `<th colspan="4">${titles[part] || part}</th>`;
    files.appendChild(heading);
    for (const name of members.sort((a, b) => rank(a) - rank(b))) addFile(name);
  }

  function addFile(name) {
    const text = result.files[name];
    const info = programOf(name);
    const number = info && isProgram(name) ? `${info.step}.` : "";
    const type = name.endsWith(".svg") ? "image/svg+xml"
      : name.endsWith(".json") ? "application/json" : "text/plain";
    const url = URL.createObjectURL(new Blob([text], { type }));
    blobUrls.push(url);
    const row = document.createElement("tr");
    row.innerHTML =
      `<td class="step">${number}</td><td>${name}</td><td>${(text.length / 1024).toFixed(0)} kB</td>` +
      `<td><a class="download" href="${url}" download="${name}">Download</a></td>`;
    if (isProgram(name)) {
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
    // A neck blank can be the neck's own plank with a block glued under
    // the headstock end once the neck is cut (neck_blank "laminated").
    const block = stock.laminated && stock.laminated.headstock_block_mm;
    if (block) {
      const glued = `${block.length} × ${block.width} × ${block.thickness} mm block under the headstock, from ${block.from_nut} mm behind the nut to past the tip`;
      rows.push(stock.blank === "laminated"
        ? [`${part} blank (laminated)`, `${stock.length_mm} × ${stock.width_mm} × ${stock.laminated.plank_thickness_mm} mm plank first; after Neck_back_finish glue a ${glued}, then the Headstock_ programs and the outline`]
        : [`${part} blank, or laminated`, `${stock.length_mm} × ${stock.width_mm} × ${stock.laminated.plank_thickness_mm} mm plank + ${glued} (neck_blank "laminated": the headstock in programs of its own)`]);
    }
  }
  const partRank = (part) => (partOrder.includes(part) ? partOrder.indexOf(part) : partOrder.length);
  const programs = Object.entries(report.gcode).sort(([, a], [, b]) => (
    partRank(a.part) - partRank(b.part) || a.step - b.step
  ));
  for (const [name, info] of programs) {
    rows.push([`${info.step}. ${name}`, `${info.tool}: ${info.estimated_minutes} min, ${(info.cutting_length_mm / 1000).toFixed(1)} m of cutting, ${info.operations.length} operations`]);
  }
  const rod = report.truss_rod;
  if (rod) {
    const chosen = rod.rod_length_mm === null
      ? `route set by hand, ${rod.route_length_mm} mm`
      : `${rod.rod_length_mm} mm rod (route ${rod.route_length_mm} mm)`;
    const advice = rod.recommended_stock_mm === null
      ? "no stock length fits"
      : `longest stock rod that fits: ${rod.recommended_stock_mm} mm`;
    rows.push(["Truss rod", `${chosen}; the neck takes up to ${rod.longest_fitting_mm} mm, ${advice}`]);
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
    ? `${name} is on the clipboard: click into the NC Viewer editor below, select all (Ctrl/Cmd+A), paste (Ctrl/Cmd+V) and press Plot — or drop the downloaded file onto it.`
    : `Could not copy to the clipboard: download ${name} and drop it onto NC Viewer below, or open it there with its file button.`;
  panel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function reset() {
  renderForm();
  clearError();
}

// ---------------------------------------------------------------------------
// Save and load a design: every form value — the instrument, the drawn body
// outline and headstock edges included — as one JSON file on the user's own
// computer.

const DESIGN_FORMAT = "cncguitarwizard-design";

function designDocument() {
  const values = collectValues();
  const { instrument, ...prototype } = values.prototype;
  return {
    format: DESIGN_FORMAT,
    version: 1,
    saved: new Date().toISOString(),
    app: window.CNCGW_MANIFEST ? window.CNCGW_MANIFEST.wheel : null,
    instrument,
    prototype,
    machining: values.machining,
  };
}

function saveDesign() {
  let design;
  try {
    design = designDocument();
  } catch (error) {
    showError(`Cannot save the design: ${error.message}`);
    return;
  }
  const blob = new Blob([JSON.stringify(design, null, 2) + "\n"], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `cncguitarwizard-${design.instrument}-${design.saved.slice(0, 10)}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  setStatus(`Saved ${link.download}`, "ok");
}

// Put one saved value into its form control, as if typed or picked.
function setControlValue(control, value) {
  if (control.tagName === "SELECT") {
    control.value = String(value);
    control.dispatchEvent(new Event("change", { bubbles: true }));
    return;
  }
  const type = control.dataset.type;
  if (type === "bool") control.checked = Boolean(value);
  else if (type === "float" || type === "int") control.value = String(value);
  else if (type === "optional_float") control.value = value === null ? "" : String(value);
  else control.value = JSON.stringify(value);
  control.dispatchEvent(new Event("input", { bubbles: true }));
  control.dispatchEvent(new Event("change", { bubbles: true }));
}

// Apply saved values to one parameter set; return the names the form
// does not know (from another version), which are skipped.
function applyValues(set, values) {
  const unknown = [];
  for (let [name, value] of Object.entries(values || {})) {
    // Older designs could name the traced DXF body; its drawn template
    // ("Design by Jone", the guitar's default body) is the same body with
    // the same placements, so the saved placements go onto it.
    if (set === "prototype" && name === "body_shape" && value?.kind === "design_by_jone") {
      const guitarBody = schema.prototype
        .flatMap((group) => group.fields)
        .find((field) => field.name === "body_shape").default;
      value = { ...guitarBody, ...value, kind: "your_design" };
    }
    const variant = form.querySelector(`.variant[data-set="${set}"][data-name="${name}"]`);
    if (variant && value && typeof value === "object" && "kind" in value) {
      const kind = variant.querySelector("select.kind");
      if (![...kind.options].some((option) => option.value === value.kind)) {
        unknown.push(`${name}.kind`);
        continue;
      }
      kind.value = value.kind;
      kind.dispatchEvent(new Event("change"));
      const { kind: _, ...fields } = value;
      unknown.push(...applyValues(`${set}.${name}`, fields).map((n) => `${name}.${n}`));
      continue;
    }
    const control = form.querySelector(`[data-set="${set}"][data-name="${name}"]`);
    if (!control) {
      unknown.push(name);
      continue;
    }
    setControlValue(control, value);
  }
  return unknown;
}

function applyDesign(design) {
  if (!design || design.format !== DESIGN_FORMAT) {
    throw new Error("This is not a CNCguitarwizard design file.");
  }
  if (!(design.instrument in schema.instruments)) {
    throw new Error(`Unknown instrument ${JSON.stringify(design.instrument)}.`);
  }
  instrumentSelect.value = design.instrument;
  instrumentSelect.dataset.current = design.instrument;
  renderForm();
  const unknown = [
    ...applyValues("prototype", design.prototype),
    ...applyValues("machining", design.machining),
  ];
  applyStringLimits();
  headstockEditor.sync();
  // The body editor draws the loaded outline, not the start shape it was
  // shown while the form was being filled in.
  bodyEditor.reloadPoints();
  bodyEditor.scheduleRefresh();
  return unknown;
}

async function loadDesign(file) {
  clearError();
  try {
    const unknown = applyDesign(JSON.parse(await file.text()));
    setStatus(`Loaded ${file.name}`, "ok");
    if (unknown.length) {
      showError(`Loaded ${file.name}, but skipped settings this version does not have: ${unknown.join(", ")}.`);
    }
  } catch (error) {
    showError(`Cannot load ${file.name}: ${error.message}`);
  }
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
    // The form may still be mid-render (the rest of it not yet attached),
    // so read it for the layout only once this render has finished.
    setTimeout(() => this.refresh(), 0);
  },

  // Take the outline from the control_points field again (after a load).
  reloadPoints() {
    if (!this.input) return;
    try {
      const points = JSON.parse(this.input.value);
      if (Array.isArray(points) && points.length >= 4) this.points = points;
    } catch (error) {
      // An unreadable field keeps the current outline.
    }
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
    this.fillTemplates();
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

  // A seven- or eight-string body opens along the centreline: each half
  // of the drawing moves out by half the widening, as in Python. The
  // stored control points stay those of the six-string drawing.
  widen([x, y]) {
    const half = (this.layout.widening || 0) / 2;
    return [x, y > 0 ? y + half : y < 0 ? y - half : y];
  },

  unwiden([x, y]) {
    const half = (this.layout.widening || 0) / 2;
    return [x, y > half ? y - half : y < -half ? y + half : 0];
  },

  outline() {
    return closedCatmullRom(this.points.map((p) => this.widen(p)), this.layout.samples_per_segment);
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

    const styles = {
      neck: { fill: "#3b2a1a", "fill-opacity": 0.85, stroke: "none" },
      pocket: { fill: "#f2c4b3", "fill-opacity": 0.9, stroke: "#7a3a1a", "stroke-width": 0.5 },
      pickup: { fill: "#f2c4b3", stroke: "#7a3a1a", "stroke-width": 0.5 },
      bridge: { fill: "#f2c4b3", stroke: "#7a3a1a", "stroke-width": 0.5 },
      top_control: { fill: "#c9b7e6", "fill-opacity": 0.55, stroke: "#5a3a8a", "stroke-width": 0.6 },
      contour_top: { fill: "#9cc79a", "fill-opacity": 0.45, stroke: "#3d6b3a", "stroke-width": 0.5 },
      contour_back: { fill: "#9aa9d6", "fill-opacity": 0.35, stroke: "#34457a", "stroke-width": 0.5, "stroke-dasharray": "3,2" },
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
      const turn = this.turnable(group) ? ", Shift-drag to turn" : "";
      this.element("title", {}, node).textContent = group ? `${name} — drag to move${turn}` : name;
    };
    for (const polygon of layout.polygons) {
      const node = this.element("path", { d: this.pathData(polygon.points), ...styles[polygon.role] }, features);
      place(node, polygon.group, polygon.name);
    }
    for (const circle of layout.circles) {
      const look = circle.rear
        ? { fill: "#fff", "fill-opacity": 0.5, stroke: "#5a3a8a", "stroke-width": 0.5, "stroke-dasharray": "2,1.5" }
        : { fill: "#fff", stroke: "#222", "stroke-width": 0.5 };
      const node = this.element("circle", { cx: circle.x, cy: -circle.y, r: circle.r, ...look }, features);
      place(node, circle.group, circle.name);
    }
    const jack = layout.jack;
    const bore = this.element("line", { x1: jack.x, y1: -jack.y, x2: jack.x2, y2: -jack.y2, stroke: "#222", "stroke-width": jack.r * 2, "stroke-opacity": 0.25 }, features);
    place(bore, jack.group, "Output jack");
    const socket = this.element("circle", { cx: jack.x, cy: -jack.y, r: jack.r, fill: "#fff", "fill-opacity": 0.6, stroke: "#222", "stroke-width": 0.8 }, features);
    place(socket, jack.group, "Output jack");

    // Square handles at the control cavity's ends and sides: dragging one
    // stretches (or shrinks) the cavity and its cover from that end, or
    // widens (narrows) them from that side.
    if (layout.control) {
      for (const along of [true, false]) {
        const points = along ? layout.control.ends : layout.control.sides;
        points.forEach(([ex, ey], end) => {
          const handle = this.element("rect", { class: `stretch-handle ${along ? "along" : "across"}`, x: ex - 3, y: -ey - 3, width: 6, height: 6 });
          handle.addEventListener("pointerdown", (event) => this.startStretch(event, along, end, handle));
          this.element("title", {}, handle).textContent = along
            ? "Control cavity end — drag to stretch or shrink it"
            : "Control cavity side — drag to widen or narrow it";
        });
      }
    }

    // A wide, invisible stroke over the outline: one click on the line
    // adds a handle there (the body inside it is left alone).
    this.outlineHit = this.element("path", { class: "outline-hit", d: this.pathData(this.outline()) });
    this.outlineHit.addEventListener("click", (event) => {
      if (event.detail <= 1) this.addPoint(event);
    });
    this.element("title", {}, this.outlineHit).textContent = "Click the outline to add a handle";

    this.handles = this.points.map((point, index) => {
      const [hx, hy] = this.widen(point);
      const handle = this.element("circle", { class: "handle", cx: hx, cy: -hy, r: 4 });
      handle.addEventListener("pointerdown", (event) => this.startDrag(event, index, handle));
      handle.addEventListener("contextmenu", (event) => { event.preventDefault(); this.removePoint(index); });
      return handle;
    });
    this.check();
    this.showTemplate();
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
      const shown = this.toModel(moveEvent);
      this.points[index] = this.unwiden(shown);
      handle.setAttribute("cx", shown[0]);
      handle.setAttribute("cy", -shown[1]);
      this.outlinePath.setAttribute("d", this.pathData(this.outline()));
      this.outlineHit.setAttribute("d", this.pathData(this.outline()));
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
    if (event.shiftKey && this.turnable(group)) {
      this.startTurn(event, group);
      return;
    }
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

  // The groups Shift-drag turns: the control cavity (with its cover, pots
  // or plate), the battery box and the jack. Round ones only move.
  turnable(group) {
    return group === "control" || group === "battery" || group === "jack";
  },

  // The point a group turns about, in the editor's frame (from the heel
  // end): the cavity's centre, or the jack's socket.
  turnCentre(group) {
    if (group === "jack") return [this.layout.jack.x, this.layout.jack.y];
    if (group === "control" && this.layout.control) return this.layout.control.centre;
    const names = group === "battery"
      ? ["Battery cavity"]
      : ["Control cavity", "Control plate recess"];
    const polygon = this.layout.polygons.find((p) => names.includes(p.name) && p.group === group)
      || this.layout.polygons.find((p) => p.group === group);
    const n = polygon.points.length;
    return [
      polygon.points.reduce((sum, p) => sum + p[0], 0) / n,
      polygon.points.reduce((sum, p) => sum + p[1], 0) / n,
    ];
  },

  startTurn(event, group) {
    const [cx, cy] = this.turnCentre(group);
    const members = [...this.svg.querySelectorAll(`[data-group="${group}"]`)];
    if (group === "control") members.push(...this.svg.querySelectorAll('[data-group^="pot:"]'));
    const bearing = (point) => Math.atan2(point[1] - cy, point[0] - cx) * 180 / Math.PI;
    const start = bearing(this.toModel(event));
    let degrees = 0;
    const move = (moveEvent) => {
      degrees = bearing(this.toModel(moveEvent)) - start;
      degrees = ((degrees + 540) % 360) - 180;
      // The SVG's Y runs down: a counter-clockwise turn in the plan is
      // a negative SVG rotation.
      for (const member of members) member.setAttribute("transform", `rotate(${-degrees} ${cx} ${-cy})`);
      this.setStatus(`Turning ${group === "control" ? "the controls" : `the ${group}`} ${Math.round(degrees * 10) / 10}°`, "");
    };
    const end = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", end);
      window.removeEventListener("pointercancel", end);
      const rounded = Math.round(degrees * 10) / 10;
      if (rounded) {
        this.applyTurn(group, rounded, [cx, cy]);
        this.refresh();
      } else {
        for (const member of members) member.removeAttribute("transform");
      }
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
  },

  // Turn a group by `degrees` (counter-clockwise in the plan) about
  // `centre`: the fields that hold its angle, and a drawn almond's own
  // pots with it.
  applyTurn(group, degrees, [cx, cy]) {
    const shape = "prototype.body_shape";
    if (group === "battery") {
      this.shiftField(shape, "battery_angle_degrees", degrees);
    } else if (group === "jack") {
      this.shiftField(shape, "jack_direction_degrees", degrees);
    } else if (group === "control") {
      this.shiftField(shape, "control_angle_degrees", degrees);
      const layoutField = this.field("prototype", "body_controls");
      if (layoutField && layoutField.value === "almond_2") {
        const input = this.field(shape, "pot_offsets");
        const angle = degrees * Math.PI / 180;
        const cos = Math.cos(angle), sin = Math.sin(angle);
        const round = (value) => Math.round(value * 10) / 10;
        const pots = readValue(input).map(([x, y]) => [
          round(cx + (x - cx) * cos - (y - cy) * sin),
          round(cy + (x - cx) * sin + (y - cy) * cos),
        ]);
        this.setField(input, pots);
      }
    }
  },

  // Drag one end of the control cavity along its long axis (or one side
  // square to it): the far end stays, so the stretch changes by the drag
  // and the centre (the cover, the pots) moves half of it toward the
  // dragged end.
  startStretch(event, along, end, handle) {
    event.preventDefault();
    event.stopPropagation();
    const [lx, ly] = this.layout.control.axis;
    const [ax, ay] = along ? [lx, ly] : [-ly, lx];
    const [ex, ey] = (along ? this.layout.control.ends : this.layout.control.sides)[end];
    const field = along ? "control_stretch" : "control_stretch_across";
    const what = along ? "longer" : "wider";
    const start = this.toModel(event);
    let moved = 0;
    handle.classList.add("dragging");
    const move = (moveEvent) => {
      const [x, y] = this.toModel(moveEvent);
      moved = Math.round(((x - start[0]) * ax + (y - start[1]) * ay) * 10) / 10;
      handle.setAttribute("x", ex + ax * moved - 3);
      handle.setAttribute("y", -(ey + ay * moved) - 3);
      const change = end === 1 ? moved : -moved;
      this.setStatus(`Control cavity ${change >= 0 ? "+" : ""}${change} mm ${what}`, "");
    };
    const finish = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", finish);
      window.removeEventListener("pointercancel", finish);
      handle.classList.remove("dragging");
      if (moved) {
        this.shiftField("prototype.body_shape", field, end === 1 ? moved : -moved);
        this.applyMove("control", [ax * moved / 2, ay * moved / 2]);
        this.refresh();
      }
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", finish);
    window.addEventListener("pointercancel", finish);
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
    } else if (group.startsWith("bolt:")) {
      // An empty list means the preset's rectangle: start from where the
      // bolts are drawn now, then move the one that was dragged.
      const input = this.field(shape, "neck_bolts");
      let bolts = readValue(input);
      if (!bolts.length) {
        bolts = this.layout.circles
          .filter((c) => c.rear && c.name.endsWith("ferrule"))
          .map((c) => [c.x, c.y]);
      }
      const target = Number(group.split(":")[1]);
      bolts = bolts.map(([x, y], index) => (
        index === target ? [round(x + dx), round(y + dy)] : [x, y]
      ));
      this.setField(input, bolts);
    } else if (group === "battery") {
      this.shiftField(shape, "battery_offset", dx);
      this.shiftField(shape, "battery_y", dy);
    } else if (group === "jack") {
      this.shiftField(shape, "jack_offset", dx);
      this.shiftField(shape, "jack_y", dy);
    } else if (group === "pickup:neck") {
      this.shiftField("prototype", "body_neck_pickup_offset", dx);
    } else if (group === "pickup:middle") {
      // Left empty the middle pickup sits halfway; a drag pins it down.
      const route = this.layout.polygons.find((p) => p.group === "pickup:middle");
      const xs = route.points.map((p) => p[0]);
      const centre = (Math.min(...xs) + Math.max(...xs)) / 2;
      this.setField(this.field("prototype", "body_middle_pickup_offset"), round(centre + dx));
    } else if (group === "pickup:bridge") {
      // The offset is measured ahead of the scale line, toward the nut.
      // Start from where the route really is: a bridge that reaches ahead
      // of the scale line (a Floyd Rose) pushes it further forward than
      // the field alone says.
      const route = this.layout.polygons.find((p) => p.group === "pickup:bridge");
      const xs = route.points.map((p) => p[0]);
      const centre = (Math.min(...xs) + Math.max(...xs)) / 2;
      // The bridge line is on the centerline scale (a multiscale's mean).
      const scale = this.layout.scale_line - this.layout.heel_end;
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
    this.points.splice(Math.floor(best / samples) + 1, 0, this.unwiden([x, y]));
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

  fillTemplates() {
    const select = document.getElementById("body-editor-template");
    if (select.options.length) return;
    // Shown when the drawing matches no template (it has been edited).
    const own = document.createElement("option");
    own.value = "";
    own.textContent = "Your own drawing";
    own.disabled = true;
    select.appendChild(own);
    for (const [key, template] of Object.entries(this.layout.templates)) {
      const option = document.createElement("option");
      option.value = key;
      option.textContent = template.label;
      select.appendChild(option);
    }
  },

  // Show the template the drawing is, or "Your own drawing" once its
  // outline has been changed.
  showTemplate() {
    const select = document.getElementById("body-editor-template");
    if (!this.layout || !select.options.length) return;
    const drawn = JSON.stringify(this.points);
    const match = Object.entries(this.layout.templates).find(
      ([, template]) => JSON.stringify(template.shape.control_points) === drawn
    );
    select.value = match ? match[0] : "";
  },

  // Replace the drawing with a template: its outline and its switch, pot
  // and jack placements, which all stay editable afterwards.
  reset() {
    if (!this.layout) return;
    const key = document.getElementById("body-editor-template").value;
    const template = this.layout.templates[key];
    if (!template) return;
    if (!window.confirm(`Replace your drawing with ${template.label}?`)) return;
    const set = "prototype.body_shape";
    for (const [name, value] of Object.entries(template.shape)) {
      if (name === "kind" || name === "control_points") continue;
      this.setField(this.field(set, name), value);
    }
    this.points = template.shape.control_points.map((p) => [...p]);
    this.commit();
    this.refresh();
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
      // Contours follow the outline itself, so they are laid out from it.
      if (polygon.role === "neck" || polygon.role.startsWith("contour")) continue;
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
// ---------------------------------------------------------------------------
// Headstock editor: drag the two edges of a "drawn" headstock over the
// fixed tuner holes. Each edge is [distance from the nut, half-width]
// points ending at the tip, joined by the same rounded curve Python uses
// (SmoothCurve), starting flat from the nut's half-width; the tip may be
// shaped with points of its own.

// A rounded curve y(x) through points, as Python's SmoothCurve: each
// interior point's slope is its neighbours' chord, the first zero, the
// last its secant; it may swing past the points.
function smoothCurve(points) {
  const n = points.length;
  const slopes = [0];
  for (let i = 1; i < n - 1; i++) {
    slopes.push((points[i + 1][1] - points[i - 1][1]) / (points[i + 1][0] - points[i - 1][0]));
  }
  slopes.push((points[n - 1][1] - points[n - 2][1]) / (points[n - 1][0] - points[n - 2][0]));
  return (x) => {
    if (x <= points[0][0]) return points[0][1];
    if (x >= points[n - 1][0]) return points[n - 1][1];
    let i = 0;
    while (points[i + 1][0] < x) i++;
    const [x0, y0] = points[i], [x1, y1] = points[i + 1];
    const w = x1 - x0, t = (x - x0) / w, t2 = t * t, t3 = t2 * t;
    return (2 * t3 - 3 * t2 + 1) * y0 + (t3 - 2 * t2 + t) * w * slopes[i]
      + (-2 * t3 + 3 * t2) * y1 + (t3 - t2) * w * slopes[i + 1];
  };
}

const headstockEditor = {
  panel: document.getElementById("headstock-editor"),
  svg: document.getElementById("headstock-editor-svg"),
  status: document.getElementById("headstock-editor-status"),
  size: document.getElementById("headstock-editor-size"),
  edges: { bass: [], treble: [] },
  // Points shaping the tip: [how far past the tip line, y], -Y to +Y.
  tip: [],
  layout: null,
  paths: {},
  hits: {},
  refreshTimer: null,

  inputs() {
    return {
      bass: form.querySelector("[data-set='prototype'][data-name='headstock_bass_edge']"),
      treble: form.querySelector("[data-set='prototype'][data-name='headstock_treble_edge']"),
      tip: form.querySelector("[data-set='prototype'][data-name='headstock_tip_points']"),
      outline: form.querySelector("[data-set='prototype'][data-name='headstock_outline']"),
    };
  },

  sync() {
    const { outline, bass, treble } = this.inputs();
    const active = outline && outline.value === "drawn";
    this.panel.classList.toggle("hidden", !active);
    if (!active) return;
    try {
      this.edges = { bass: JSON.parse(bass.value), treble: JSON.parse(treble.value) };
    } catch (error) {
      this.edges = { bass: [], treble: [] };
    }
    try {
      this.tip = JSON.parse(this.inputs().tip.value);
    } catch (error) {
      this.tip = [];
    }
    this.refresh();
  },

  async refresh() {
    if (this.panel.classList.contains("hidden") || !pyodide) return;
    let payload;
    try {
      payload = collectValues();
    } catch (error) {
      this.setStatus(`Cannot place the tuners: ${error.message}`, "bad");
      return;
    }
    pyodide.globals.set("payload_json", JSON.stringify(payload));
    const layout = await runPython(
      "import json\nfrom cncguitarwizard.webapp import headstock_editor_layout\n" +
      "json.dumps(headstock_editor_layout(json.loads(payload_json)))"
    );
    if (layout.error) {
      this.setStatus(layout.error, "bad");
      return;
    }
    this.layout = layout;
    // Until a handle is moved the edge fields stay empty and the drawing
    // follows the fitted outline (a changed style or length redraws it);
    // the first edit writes the edges.
    if (this.untouched()) {
      this.edges = structuredClone(layout.start_edges);
      this.tip = [];
    }
    this.draw();
  },

  untouched() {
    const { bass, treble } = this.inputs();
    try {
      return !JSON.parse(bass.value).length || !JSON.parse(treble.value).length;
    } catch (error) {
      return true;
    }
  },

  scheduleRefresh() {
    clearTimeout(this.refreshTimer);
    this.refreshTimer = setTimeout(() => this.refresh(), 400);
  },

  element(name, attributes, parent) {
    return bodyEditor.element.call({ svg: this.svg }, name, attributes, parent);
  },

  // Y of a side's edge from its half-width, in the model frame.
  sign(side) {
    return (side === "bass" ? 1 : -1) * this.layout.bass_sign;
  },

  length() {
    return this.edges.bass[this.edges.bass.length - 1][0];
  },

  curve(side) {
    return smoothCurve([[0, this.layout.nut_half_width], ...this.edges[side]]);
  },

  // The tip corners' Y, low (-Y) and high (+Y).
  tipCorners() {
    const ys = ["bass", "treble"].map((side) => this.sign(side) * this.edges[side][this.edges[side].length - 1][1]);
    return [Math.min(...ys), Math.max(...ys)];
  },

  // Model Y of the +Y (1) or -Y (-1) edge at a distance from the nut.
  edgeY(distance, ySign) {
    const side = ySign * this.layout.bass_sign > 0 ? "bass" : "treble";
    return ySign * this.curve(side)(distance);
  },

  // The tip as model points from its -Y corner to its +Y corner, as
  // Python's HeadstockPlan.tip_outline: straight without tip points,
  // else a Catmull-Rom curve through them leaving each corner along its
  // edge.
  tipOutline() {
    const length = this.length();
    const low = [-length, this.edgeY(length, -1)], high = [-length, this.edgeY(length, 1)];
    if (!this.tip.length) return [low, high];
    const points = [low, ...this.tip.map(([past, y]) => [-(length + past), y]), high];
    const step = Math.min(0.5, length / 10);
    const direction = (ySign) => {
      const slope = (this.edgeY(length, ySign) - this.edgeY(length - step, ySign)) / step;
      const norm = Math.hypot(1, slope);
      return [-1 / norm, slope / norm];
    };
    const n = points.length;
    const tangents = points.map((point, i) => {
      if (i === 0) {
        const chord = Math.hypot(points[1][0] - point[0], points[1][1] - point[1]);
        const [dx, dy] = direction(-1);
        return [dx * chord, dy * chord];
      }
      if (i === n - 1) {
        const chord = Math.hypot(points[n - 2][0] - point[0], points[n - 2][1] - point[1]);
        const [dx, dy] = direction(1);
        return [-dx * chord, -dy * chord];
      }
      return [(points[i + 1][0] - points[i - 1][0]) / 2, (points[i + 1][1] - points[i - 1][1]) / 2];
    });
    const samples = [points[0]];
    for (let i = 0; i < n - 1; i++) {
      const [p0, p1, m0, m1] = [points[i], points[i + 1], tangents[i], tangents[i + 1]];
      for (let k = 1; k <= 16; k++) {
        const t = k / 16, t2 = t * t, t3 = t2 * t;
        const h00 = 2 * t3 - 3 * t2 + 1, h10 = t3 - 2 * t2 + t, h01 = -2 * t3 + 3 * t2, h11 = t3 - t2;
        samples.push([0, 1].map((c) => h00 * p0[c] + h10 * m0[c] + h01 * p1[c] + h11 * m1[c]));
      }
    }
    return samples;
  },

  // The tip from the bass corner to the treble corner, for the outline.
  tipSamples() {
    const tip = this.tipOutline();
    return this.sign("bass") < 0 ? tip : [...tip].reverse();
  },

  // How far a point lies from the tip's outline (as Python measures it).
  tipClearance(x, y) {
    const tip = this.tipOutline();
    let best = Infinity;
    for (let i = 0; i + 1 < tip.length; i++) {
      const [ax, ay] = tip[i], [bx, by] = tip[i + 1];
      const dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy;
      const t = l2 ? Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / l2)) : 0;
      best = Math.min(best, Math.hypot(x - (ax + t * dx), y - (ay + t * dy)));
    }
    return best;
  },

  reach() {
    return Math.max(this.length(), ...this.tipOutline().map(([x]) => -x));
  },

  // The outline as model points: one side nut to tip, the other back.
  samples(side) {
    const length = this.length(), step = this.layout.sample_step;
    const distances = new Set([0, length, ...this.edges[side].map((p) => p[0])]);
    for (let d = step; d < length; d += step) distances.add(d);
    const curve = this.curve(side), sign = this.sign(side);
    return [...distances].sort((a, b) => a - b).map((d) => [-d, sign * curve(d)]);
  },

  pathData(points) {
    return points.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(2)},${(-y).toFixed(2)}`).join(" ");
  },

  draw() {
    const layout = this.layout;
    this.svg.innerHTML = "";
    const bass = this.samples("bass"), treble = this.samples("treble");
    const tip = this.tipSamples();
    const all = [...bass, ...treble, ...tip, ...layout.holes.map((h) => [h.x, h.y])];
    const xs = all.map((p) => p[0]), ys = all.map((p) => p[1]);
    const margin = 25;
    const minX = Math.min(...xs) - margin, maxX = 70;
    const minY = Math.min(...ys) - margin, maxY = Math.max(...ys) + margin;
    this.svg.setAttribute("viewBox", `${minX} ${-maxY} ${maxX - minX} ${maxY - minY}`);
    const grid = this.element("g", { stroke: "#eee6d8", "stroke-width": 0.3 });
    for (let x = Math.ceil(minX / 10) * 10; x <= maxX; x += 10) this.element("line", { x1: x, y1: -maxY, x2: x, y2: -minY }, grid);
    for (let y = Math.ceil(minY / 10) * 10; y <= maxY; y += 10) this.element("line", { x1: minX, y1: -y, x2: maxX, y2: -y }, grid);
    this.element("line", { x1: minX, y1: 0, x2: maxX, y2: 0, stroke: "#bbb", "stroke-width": 0.4, "stroke-dasharray": "3,2" });
    // The neck past the nut, for scale.
    const half = layout.nut_half_width;
    this.element("rect", { x: 0, y: -half, width: 70, height: 2 * half, fill: "#3b2a1a", "fill-opacity": 0.85 });
    this.element("path", {
      d: this.pathData([...bass, ...tip.slice(1, -1), ...[...treble].reverse()]) + " Z",
      fill: "#f1e4c8", stroke: "none",
    });
    for (const side of ["bass", "treble"]) {
      const points = side === "bass" ? bass : treble;
      this.paths[side] = this.element("path", {
        d: this.pathData(points),
        fill: "none", stroke: "#6b4a1f", "stroke-width": 0.8, "stroke-linecap": "round",
      });
      // A wide, invisible stroke over the edge: one click adds a handle.
      const hit = this.element("path", { class: "outline-hit", d: this.pathData(points), "stroke-width": 4 });
      hit.addEventListener("click", (event) => {
        if (event.detail <= 1) this.addPoint(event, side);
      });
      this.element("title", {}, hit).textContent = "Click the edge to add a handle";
      this.hits = { ...this.hits, [side]: hit };
    }
    this.tipLine = this.element("path", {
      d: this.pathData(tip), fill: "none",
      stroke: "#6b4a1f", "stroke-width": 0.8, "stroke-linejoin": "round",
    });
    // One click on the tip adds a point that shapes it.
    this.tipHit = this.element("path", { class: "outline-hit", d: this.pathData(tip), "stroke-width": 4 });
    this.tipHit.addEventListener("click", (event) => {
      if (event.detail <= 1) this.addTipPoint(event);
    });
    this.element("title", {}, this.tipHit).textContent = "Click the tip to add a handle";
    for (const hole of layout.holes) {
      this.element("circle", { cx: hole.x, cy: -hole.y, r: hole.r, fill: "#fff", stroke: "#222", "stroke-width": 0.4, "pointer-events": "none" });
      this.element("circle", { cx: hole.x, cy: -hole.y, r: layout.min_edge_distance, fill: "none", stroke: "#8a4b1e", "stroke-width": 0.25, "stroke-dasharray": "1.5,1.5", "pointer-events": "none" });
    }
    for (const side of ["bass", "treble"]) {
      const sign = this.sign(side);
      this.edges[side].forEach(([d, h], index) => {
        const handle = this.element("circle", { class: "handle", cx: -d, cy: -sign * h, r: 2.2 });
        handle.addEventListener("pointerdown", (event) => this.startDrag(event, side, index, handle));
        handle.addEventListener("contextmenu", (event) => { event.preventDefault(); this.removePoint(side, index); });
      });
    }
    this.tip.forEach(([past, y], index) => {
      const handle = this.element("circle", { class: "handle", cx: -(this.length() + past), cy: -y, r: 2.2 });
      handle.addEventListener("pointerdown", (event) => this.startTipDrag(event, index, handle));
      handle.addEventListener("contextmenu", (event) => { event.preventDefault(); this.removeTipPoint(index); });
    });
    this.check();
  },

  toModel(event) {
    return bodyEditor.toModel.call({ svg: this.svg }, event);
  },

  // Move one handle; a tip handle sets the length of both edges.
  place(side, index, [x, y]) {
    const edge = this.edges[side];
    const isTip = index === edge.length - 1;
    const half = Math.round(y * this.sign(side) * 10) / 10;
    let distance = Math.round(-x * 10) / 10;
    if (isTip) {
      const before = Math.max(
        ...["bass", "treble"].map((s) => (this.edges[s].length > 1 ? this.edges[s][this.edges[s].length - 2][0] : 0))
      );
      distance = Math.max(distance, before + 2);
      for (const s of ["bass", "treble"]) this.edges[s][this.edges[s].length - 1][0] = distance;
    } else {
      const low = index > 0 ? edge[index - 1][0] + 1 : 1;
      distance = Math.min(Math.max(distance, low), edge[index + 1][0] - 1);
      edge[index][0] = distance;
    }
    edge[index][1] = half;
  },

  startDrag(event, side, index, handle) {
    if (event.altKey) {
      this.removePoint(side, index);
      return;
    }
    event.preventDefault();
    handle.classList.add("dragging");
    const move = (moveEvent) => {
      this.place(side, index, this.toModel(moveEvent));
      const bass = this.samples("bass"), treble = this.samples("treble");
      this.paths.bass.setAttribute("d", this.pathData(bass));
      this.paths.treble.setAttribute("d", this.pathData(treble));
      this.hits.bass.setAttribute("d", this.pathData(bass));
      this.hits.treble.setAttribute("d", this.pathData(treble));
      const tip = this.tipSamples();
      this.tipLine.setAttribute("d", this.pathData(tip));
      this.tipHit.setAttribute("d", this.pathData(tip));
      const [d, h] = this.edges[side][index];
      handle.setAttribute("cx", -d);
      handle.setAttribute("cy", -this.sign(side) * h);
      this.check();
    };
    const end = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", end);
      window.removeEventListener("pointercancel", end);
      this.commit();
      this.draw();
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
  },

  addPoint(event, side) {
    const [x, y] = this.toModel(event);
    const distance = Math.round(-x * 10) / 10;
    const edge = this.edges[side];
    const index = edge.findIndex(([d]) => d > distance);
    if (index < 0 || distance <= 1 || (index > 0 && distance - edge[index - 1][0] < 1)) return;
    edge.splice(index, 0, [distance, Math.round(y * this.sign(side) * 10) / 10]);
    this.commit();
    this.draw();
  },

  // A tip point keeps between its neighbours across the tip.
  placeTip(index, [x, y]) {
    const [low, high] = this.tipCorners();
    const below = index > 0 ? this.tip[index - 1][1] : low;
    const above = index + 1 < this.tip.length ? this.tip[index + 1][1] : high;
    const clampedY = Math.min(Math.max(y, below + 0.5), above - 0.5);
    this.tip[index] = [Math.round((-x - this.length()) * 10) / 10, Math.round(clampedY * 10) / 10];
  },

  startTipDrag(event, index, handle) {
    if (event.altKey) {
      this.removeTipPoint(index);
      return;
    }
    event.preventDefault();
    handle.classList.add("dragging");
    const move = (moveEvent) => {
      this.placeTip(index, this.toModel(moveEvent));
      const tip = this.tipSamples();
      this.tipLine.setAttribute("d", this.pathData(tip));
      this.tipHit.setAttribute("d", this.pathData(tip));
      const [past, y] = this.tip[index];
      handle.setAttribute("cx", -(this.length() + past));
      handle.setAttribute("cy", -y);
      this.check();
    };
    const end = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", end);
      window.removeEventListener("pointercancel", end);
      this.commit();
      this.draw();
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
  },

  addTipPoint(event) {
    const [x, y] = this.toModel(event);
    const [low, high] = this.tipCorners();
    if (y <= low + 0.5 || y >= high - 0.5 || this.tip.some(([, py]) => Math.abs(py - y) < 0.5)) return;
    this.tip.push([Math.round((-x - this.length()) * 10) / 10, Math.round(y * 10) / 10]);
    this.tip.sort((a, b) => a[1] - b[1]);
    this.commit();
    this.draw();
  },

  removeTipPoint(index) {
    this.tip.splice(index, 1);
    this.commit();
    this.draw();
  },

  removePoint(side, index) {
    if (index === this.edges[side].length - 1) {
      this.setStatus("The tip handle sets the length and cannot be removed.", "bad");
      return;
    }
    this.edges[side].splice(index, 1);
    this.commit();
    this.draw();
  },

  // Back to the fitted outline: the edge fields are emptied, so the
  // drawing follows the fitted outline again until the next edit.
  reset() {
    if (!this.layout || !window.confirm("Replace the drawn headstock with the fitted outline?")) return;
    const { bass, treble, tip } = this.inputs();
    bodyEditor.setField(bass, []);
    bodyEditor.setField(treble, []);
    bodyEditor.setField(tip, []);
    this.edges = structuredClone(this.layout.start_edges);
    this.tip = [];
    this.draw();
  },

  commit() {
    const { bass, treble, tip } = this.inputs();
    bodyEditor.setField(bass, this.edges.bass);
    bodyEditor.setField(treble, this.edges.treble);
    bodyEditor.setField(tip, this.tip);
  },

  // Every hole must keep min_edge_distance from the edges and the tip,
  // measured across the neck at the hole and along it to the tip, as the
  // fitted outline is laid out (and as Python checks it).
  check() {
    const limit = this.layout.min_edge_distance;
    const bassCurve = this.curve("bass"), trebleCurve = this.curve("treble");
    const edgeY = (distance, ySign) => {
      const side = ySign * this.layout.bass_sign > 0 ? "bass" : "treble";
      return ySign * (side === "bass" ? bassCurve : trebleCurve)(distance);
    };
    const close = [];
    for (const hole of this.layout.holes) {
      const distance = -hole.x;
      const gap = Math.min(
        edgeY(distance, 1) - hole.y,
        hole.y - edgeY(distance, -1),
        this.tipClearance(hole.x, hole.y),
      );
      if (gap < limit - 0.5) close.push(`${hole.side} at ${distance.toFixed(0)} mm (${gap.toFixed(1)} mm)`);
    }
    this.size.textContent = `— ${this.reach().toFixed(0)} mm long`;
    const [low, high] = this.tipCorners();
    if (this.tip.some(([, y]) => y <= low || y >= high)) {
      this.setStatus("A tip handle lies outside the tip's corners: move it in or remove it.", "bad");
    } else if (close.length) {
      this.setStatus(`Too close to the edge (keep ${limit} mm): ${close.join(", ")}.`, "bad");
    } else {
      this.setStatus(`Every tuner hole is at least ${limit} mm from the edge.`, "ok");
    }
  },

  setStatus(text, kind) {
    this.status.textContent = text;
    this.status.className = `note ${kind}`;
  },
};

document.getElementById("headstock-editor-reset").addEventListener("click", () => headstockEditor.reset());
form.addEventListener("change", (event) => {
  if (event.target.dataset.name === "headstock_outline") headstockEditor.sync();
  else if (!/^headstock_(bass_edge|treble_edge|tip_points)$/.test(event.target.dataset.name || "")) headstockEditor.scheduleRefresh();
});
form.addEventListener("input", (event) => {
  if (/^headstock_(treble_edge|bass_edge|tip_points)$/.test(event.target.dataset.name || "")) return;
  headstockEditor.scheduleRefresh();
});

form.addEventListener("input", (event) => {
  if (event.target.dataset.name !== "control_points") {
    bodyEditor.scheduleRefresh();
    return;
  }
  // Points typed into the JSON field, or loaded from a saved design, are
  // the editor's from now on, even before it has a layout to draw them on.
  try {
    const points = JSON.parse(event.target.value);
    if (Array.isArray(points) && points.length >= 4) {
      bodyEditor.points = points;
      if (bodyEditor.layout) bodyEditor.draw();
    }
  } catch (error) {
    // Keep the last good drawing while the text is being edited.
  }
});
form.addEventListener("change", (event) => {
  if (event.target.dataset.name === "string_count") applyStringLimits();
  if (event.target.dataset.name !== "control_points") bodyEditor.scheduleRefresh();
});

instrumentSelect.addEventListener("change", () => {
  if (form.querySelector(".changed") && !window.confirm(
    "Switch instrument? Every value goes back to that instrument's defaults."
  )) {
    instrumentSelect.value = instrumentSelect.dataset.current;
    return;
  }
  instrumentSelect.dataset.current = instrumentSelect.value;
  renderForm();
  clearError();
});

buildButton.addEventListener("click", build);
resetButton.addEventListener("click", reset);
saveDesignButton.addEventListener("click", saveDesign);
loadDesignButton.addEventListener("click", () => {
  if (form.querySelector(".changed") && !window.confirm(
    "Load a design? Every current value is replaced by the file's."
  )) return;
  loadDesignFile.click();
});
loadDesignFile.addEventListener("change", () => {
  const [file] = loadDesignFile.files;
  loadDesignFile.value = "";
  if (file) loadDesign(file);
});
showAdvanced.addEventListener("change", applyAdvancedToggle);
boot();
