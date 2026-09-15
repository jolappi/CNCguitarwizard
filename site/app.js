/* CNCguitarwizard in the browser: load Pyodide, install the package wheel,
   draw a form from the dataclass schema, run the build, offer downloads. */

const PYODIDE_INDEX = "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/";

const status = document.getElementById("status");
const form = document.getElementById("form");
const buildButton = document.getElementById("build");
const resetButton = document.getElementById("reset");
const errorBox = document.getElementById("error");
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
    const manifest = await (await fetch("wheel.json", { cache: "no-store" })).json();
    const micropip = pyodide.pyimport("micropip");
    await micropip.install(new URL("wheels/" + manifest.wheel, location.href).href);
    const schemaJson = await pyodide.runPythonAsync(
      "import json\nfrom cncguitarwizard.webapp import parameter_schema\njson.dumps(parameter_schema())"
    );
    schema = JSON.parse(schemaJson);
    renderForm();
    buildButton.disabled = false;
    resetButton.disabled = false;
    setStatus("Ready — " + manifest.wheel, "ok");
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
  if (field.type === "bool") {
    input.type = "checkbox";
    input.checked = Boolean(field.default);
  } else if (field.type === "float" || field.type === "int") {
    input.type = "number";
    input.step = field.type === "int" ? "1" : "any";
    input.value = String(field.default);
  } else {
    input.type = "text";
    input.value = field.type === "optional_float" && field.default === null
      ? ""
      : JSON.stringify(field.default);
  }
  input.addEventListener("input", () => markChanged(input));
  row.appendChild(label);
  row.appendChild(input);
  return row;
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
    payload[input.dataset.set][input.dataset.name] = value;
  }
  return payload;
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
  setStatus("Building…");
  const started = performance.now();
  try {
    pyodide.globals.set("payload_json", JSON.stringify(payload));
    const resultJson = await pyodide.runPythonAsync(
      "import json\nfrom cncguitarwizard.webapp import run_build\n" +
      "json.dumps(run_build(json.loads(payload_json)))"
    );
    const result = JSON.parse(resultJson);
    if (result.error) {
      showError(result.error);
      setStatus("Parameters rejected", "bad");
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
    if (index === 1 || (previews.length === 1 && index === 0)) button.click();
  });

  const files = document.getElementById("files");
  files.innerHTML = "<tr><th>File</th><th>Size</th><th></th></tr>";
  const order = [
    "Prototype001_freecad.py", "Prototype001.FCMacro",
    "Body_index_pins.nc", "Body_top.nc", "Body_back.nc",
    "Body_index_pins.svg", "Body_top.svg", "Body_back.svg", "build.json",
  ];
  const names = Object.keys(result.files).sort(
    (a, b) => (order.indexOf(a) + 1 || 99) - (order.indexOf(b) + 1 || 99)
  );
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
  const rows = [
    ["Stock", `${report.stock.length_mm} × ${report.stock.width_mm} × ${report.stock.thickness_mm} mm`],
    ["Work origin (model X/Y)", report.stock.work_origin_model_xy.join(", ")],
  ];
  for (const [name, info] of Object.entries(report.gcode)) {
    rows.push([name, `${info.estimated_minutes} min, ${(info.cutting_length_mm / 1000).toFixed(1)} m of cutting, ${info.operations.length} operations`]);
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
