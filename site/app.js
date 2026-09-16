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
      for (const field of group.fields) holder.appendChild(renderField(set, field));
      details.appendChild(holder);
      form.appendChild(details);
    }
  }
}

function renderField(set, field) {
  if (field.type === "variant") return renderVariantField(set, field);
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
    for (const subfield of field.variants[kind].fields) {
      const withValue = values && subfield.name in values
        ? { ...subfield, default: subfield.default, value: values[subfield.name] }
        : subfield;
      const subrow = renderField(set + "." + field.name, withValue);
      sub.appendChild(subrow);
    }
    select.classList.toggle("changed", kind !== field.default.kind);
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

function reset() {
  renderForm();
  clearError();
}

buildButton.addEventListener("click", build);
resetButton.addEventListener("click", reset);
boot();
