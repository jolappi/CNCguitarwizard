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
const findSetting = document.getElementById("find-setting");
const changedOnly = document.getElementById("changed-only");
const filterEmpty = document.getElementById("filter-empty");
const instrumentSelect = document.getElementById("instrument");
const saveDesignButton = document.getElementById("save-design");
const guitarName = document.getElementById("guitar-name");
const ncZipButton = document.getElementById("download-nc-zip");
const loadDesignButton = document.getElementById("load-design");
const loadDesignFile = document.getElementById("load-design-file");

let pyodide = null;
let schema = null;
let blobUrls = [];

// Ask a yes/no question in the page's own dialog; resolves true for OK.
// (window.confirm is answered unseen in some embedded browsers.)
function askConfirm(message) {
  const dialog = document.getElementById("confirm-dialog");
  dialog.querySelector(".message").textContent = message;
  dialog.returnValue = "";
  return new Promise((resolve) => {
    dialog.addEventListener("close", () => resolve(dialog.returnValue === "yes"), { once: true });
    dialog.showModal();
  });
}

function setStatus(text, kind) {
  status.textContent = text;
  status.className = kind || "";
}

// An error above the result; one about a field (a value that cannot be
// read) has a button that goes to it.
function showError(message, field = null) {
  errorBox.textContent = message;
  if (field) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary";
    button.textContent = `Go to ${fieldLabel(field.dataset.name)}`;
    button.addEventListener("click", () => goToField(field));
    errorBox.append("\n", button);
  }
  errorBox.classList.remove("hidden");
  bringIntoView(errorBox);
}

// Show a form field and select it: its group and folds opened (a search
// that leaves it out cleared), or its copy in an editor's Settings while
// that editor is shown.
function goToField(field) {
  const row = field.closest(".field");
  let control = field;
  if (row.classList.contains("mirrored") && mirrors.has(field)) {
    syncMirrors();  // the copy shows the field's value and mark
    control = mirrors.get(field);
  } else if (form.classList.contains("filtering") && !row.classList.contains("match")) {
    findSetting.value = "";
    changedOnly.checked = false;
    applyFormFilter();
  }
  for (let fold = control.closest("details"); fold; fold = fold.parentElement.closest("details")) fold.open = true;
  control.focus();
  if (control.tagName === "INPUT") control.select();
}

// The build's result and errors sit first in the right-hand column (under
// the build button on a narrow screen): scroll one there if it arrives out
// of view.
function bringIntoView(element) {
  const top = element.getBoundingClientRect().top;
  if (top < 0 || top > window.innerHeight - 120) {
    element.scrollIntoView({ behavior: "smooth", block: "start" });
  }
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
    undoHistory.start();
    // The design the page was last left with, kept in this browser (said
    // so unless it is the defaults).
    const defaults = undoHistory.current;
    const restored = restoreLastDesign();
    autosaveReady = true;
    undoHistory.start();
    const changed = restored && undoHistory.current !== defaults;
    setStatus(`Ready — ${manifest.wheel} (build ${manifest.build || "dev"})` +
      (changed ? " · your last design is back (Reset starts afresh)" : ""), "ok");
    // The first visit begins with the tour, once the drawings are laid out.
    let toured = true;
    try {
      toured = localStorage.getItem(TOURED) !== null;
    } catch {
      // No storage: no tour unasked, as it could not be remembered.
    }
    if (!toured) setTimeout(startTour, 1200);
  } catch (error) {
    console.error(error);
    setStatus("Failed to start", "bad");
    showError("The Python runtime could not be started:\n" + error);
  }
}

function renderForm() {
  form.innerHTML = "";
  const opened = savedOpenGroups();
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
      details.className = "group";
      details.dataset.title = group.title;
      details.open = opened ? opened.includes(group.title) : group.title === "Body" || group.title === "Machining";
      details.addEventListener("toggle", saveOpenGroups);
      const summary = document.createElement("summary");
      summary.textContent = group.title;
      const count = document.createElement("span");
      count.className = "changed-count";
      summary.appendChild(count);
      details.appendChild(summary);
      const holder = document.createElement("div");
      holder.className = "fields";
      holder.appendChild(groupResetRow(details));
      renderFieldList(set, group.fields, holder);
      details.appendChild(holder);
      form.appendChild(details);
    }
  }
  applyAdvancedToggle();
  applyStringLimits();
  mirrorEditorFields();
  headstockEditor.fillTemplates();
  inlayEditor.fillTemplates();
  syncBodyButtons();
  countChanged();
  foldsBeforeFinding = null;
  applyFormFilter();
  setTimeout(() => headstockEditor.sync(), 0);
  setTimeout(() => inlayEditor.refresh(), 0);
  undoHistory.note();
}

// The settings that shape an editor's drawing are shown in its own pane:
// each is a copy of the form's field, which stays the one that is saved,
// loaded and built (its row in the form is hidden while the pane is shown).
// A change on either side is passed to the other.
// Every setting that changes an editor's drawing sits above it (its row in
// the form hidden meanwhile), but the instrument-wide ones (scale, strings,
// handedness, nut width) that change every drawing, and the fine sizes
// behind each group's Advanced fold.
const EDITOR_FIELDS = {
  "body-editor-options": [
    "neck_joint", "body_pickups", "body_neck_pickup", "body_middle_pickup", "body_bridge_pickup",
    "body_neck_pickup_offset", "body_middle_pickup_offset", "body_bridge_pickup_offset", "body_pickups_follow_fan",
    "body_bridge", "body_bridge_follows_fan", "body_controls", "body_switch", "body_jack",
    "body_pickguard", "body_pickguard_style", "body_pickup_frame", "body_pickup_frame_direction",
    "body_arm_contour_depth", "body_belly_cut_depth", "body_carved_top", "body_carve_depth", "body_stepped_top",
    "body_engraving", "body_engraving_pattern", "body_engraving_seed", "body_battery_box", "body_battery_count",
    "body_neck_bolts_outward",
  ],
  "headstock-editor-options": [
    "headstock_style", "headstock_bass_side", "headstock_length", "tuner_hole_diameter", "nut_style", "locking_nut",
    "headstock_engraving_text", "headstock_engraving_font", "headstock_engraving_height", "headstock_engraving_angle",
    "truss_rod_adjustment", "truss_rod_spoke_wheel", "truss_rod_cover_style", "truss_rod_cover_length",
    "truss_rod_cover_width",
  ],
  "inlay-editor-options": [
    "inlay_style", "inlay_single_marker_frets", "inlay_double_marker_frets", "inlay_dot_diameter",
    "inlay_block_length_fraction", "inlay_block_edge_margin", "inlay_depth", "fretboard_binding_width",
  ],
};
const mirrors = new Map();

function mirrorEditorFields() {
  mirrors.clear();
  for (const [id, names] of Object.entries(EDITOR_FIELDS)) {
    const holder = document.getElementById(id);
    holder.innerHTML = "";
    for (const name of names) {
      // A plain field, or a variant's kind (the bridge: its own sizes
      // stay in the form).
      const original = form.querySelector(`:is(input, select)[data-set="prototype"][data-name="${name}"]`)
        || form.querySelector(`.variant[data-set="prototype"][data-name="${name}"] select.kind`);
      if (!original) continue;
      const row = original.closest(".field");
      const copy = original.cloneNode(true);
      copy.id = `${id}.${name}`;
      delete copy.dataset.set;
      delete copy.dataset.name;
      const label = document.createElement("label");
      label.textContent = fieldLabel(name);
      label.htmlFor = copy.id;
      // The form row's explanation goes with it.
      if (row.title) {
        label.title = copy.title = row.title;
        label.classList.add("explained");
      }
      // Only a value that reads is passed on; one that does not is
      // marked as the form's own fields are (see markChanged).
      const pass = (event) => {
        if (copy.tagName === "INPUT") {
          if (valueProblem(copy)) {
            if (event.type === "change") copy.classList.add("invalid");
            return;
          }
          copy.classList.remove("invalid");
        }
        setControlValue(original, copy.tagName === "SELECT" ? copy.value : readValue(copy));
      };
      copy.addEventListener("change", pass);
      if (copy.tagName !== "SELECT") copy.addEventListener("input", pass);
      holder.append(label, name.endsWith("_seed") ? withReroll(copy, original) : copy);
      mirrors.set(original, copy);
    }
    const summary = holder.closest("details.editor-settings")?.querySelector(":scope > summary");
    if (summary) summary.textContent = `Settings (${holder.querySelectorAll("label").length})`;
  }
  syncMirrors();
  showMirroredRows();
}

// A hidden pane (a fitted or headless headstock has no editor) gives its
// settings back to the form, where they can still be seen and changed.
function showMirroredRows() {
  for (const [original, copy] of mirrors) {
    const shown = !copy.closest(".body-editor").classList.contains("hidden");
    original.closest(".field")?.classList.toggle("mirrored", shown);
  }
}

function syncMirrors() {
  for (const [original, copy] of mirrors) {
    if (copy.type === "checkbox") copy.checked = original.checked;
    else if (document.activeElement !== copy) {
      copy.value = original.value;
      copy.classList.toggle("invalid", original.classList.contains("invalid"));
    }
    if (copy.tagName === "SELECT") {
      // Kinds hidden for the string count are hidden here too.
      [...copy.options].forEach((option, index) => {
        option.hidden = original.options[index].hidden;
        option.disabled = original.options[index].disabled;
      });
    }
    copy.classList.toggle("changed", original.classList.contains("changed"));
  }
  // A folded Settings shows that something in it is changed.
  for (const details of document.querySelectorAll("details.editor-settings")) {
    details.querySelector(":scope > summary").classList.toggle(
      "changed", details.querySelector(".editor-options .changed") !== null);
  }
}

form.addEventListener("change", syncMirrors);
form.addEventListener("input", syncMirrors);

// Hide the kinds not made for the instrument's string count (the
// Tune-o-matic past six strings, the Kahler and Floyd Rose outside six to
// eight); if one of them is chosen, switch to the first kind that fits.
function instrumentStrings() {
  const countInput = form.querySelector('[data-set="prototype"][data-name="string_count"]');
  return countInput ? readValue(countInput) : 6;
}

// A bridge with a string count of its own (a hardtail's holes, a Floyd
// Rose's or Kahler's size) keeps it with the instrument's.
function syncStringCount(holder) {
  const count = instrumentStrings();
  const own = holder.querySelector(`[data-set="prototype.${holder.dataset.name}"][data-name="string_count"]`);
  if (own && readValue(own) !== count) {
    own.value = String(count);
    markChanged(own);
  }
}

function applyStringLimits() {
  const count = instrumentStrings();
  for (const holder of form.querySelectorAll(".variant")) {
    const field = variantFields[holder.dataset.name];
    if (!field) continue;
    const select = holder.querySelector("select.kind");
    for (const option of select.options) {
      const { max_strings: most, min_strings: least } = field.variants[option.value];
      const unfit = (most != null && count > most) || (least != null && count < least);
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
    syncStringCount(holder);
  }
  syncMirrors();
}

// Basic fields first; the rarely changed ones fold away behind
// "Advanced", whose summary lights up when one of them has been edited.
// ``title`` names the fold when nothing above it does (the body shape,
// whose single kind has no dropdown).
// The groups opened by hand are kept in the browser, so a reload (or
// another instrument, a loaded design) opens the same ones; without any
// kept, Body and Machining open.
const OPEN_GROUPS = "cncguitarwizard.openGroups";

function savedOpenGroups() {
  try {
    const titles = JSON.parse(localStorage.getItem(OPEN_GROUPS));
    return Array.isArray(titles) ? titles : null;
  } catch {
    return null;  // no storage (a private window), or nothing readable kept
  }
}

function saveOpenGroups() {
  // A search opens the groups it finds in; that is not kept.
  if (form.classList.contains("filtering")) return;
  const titles = [...form.querySelectorAll(":scope > details.group[open]")].map((group) => group.dataset.title);
  try {
    localStorage.setItem(OPEN_GROUPS, JSON.stringify(titles));
  } catch {
    // No storage: the groups open as by default next time.
  }
}

function renderFieldList(set, fields, holder, title) {
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
  summary.textContent = title
    ? `${fieldLabel(title)} — Advanced (${advanced.length})`
    : `Advanced (${advanced.length})`;
  details.appendChild(summary);
  const inner = document.createElement("div");
  inner.className = "fields";
  for (const field of advanced) inner.appendChild(renderField(set, field));
  details.appendChild(inner);
  details.addEventListener("input", () => flagAdvancedSummary(details));
  details.addEventListener("change", () => flagAdvancedSummary(details));
  holder.appendChild(details);
}

// Each group of the form says how many of its settings are changed from
// their defaults (an editor pane's too, whose rows the form keeps), with
// a button to put them back, and "Show only the settings changed" how
// many there are in all.
function countChanged() {
  let total = 0;
  for (const group of form.querySelectorAll(":scope > details.group")) {
    const changed = group.querySelectorAll("input.changed, select.changed").length;
    group.querySelector(":scope > summary .changed-count").textContent = changed ? ` · ${changed} changed` : "";
    const resetRow = group.querySelector(".group-reset");
    resetRow.hidden = changed === 0;
    resetRow.firstChild.textContent = `Reset ${changed} to default${changed === 1 ? "" : "s"}`;
    total += changed;
  }
  document.getElementById("changed-total").textContent = total ? ` (${total})` : "";
}
form.addEventListener("change", countChanged);
form.addEventListener("input", countChanged);

// The row at the top of a group with its Reset button (see countChanged).
function groupResetRow(group) {
  const row = document.createElement("div");
  row.className = "group-reset";
  row.hidden = true;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "secondary";
  button.title = "Put this group's changed settings back to their defaults (Undo takes them back)";
  button.addEventListener("click", () => resetGroup(group));
  row.appendChild(button);
  return row;
}

// A group's changed settings (and any that cannot be read) back to their
// defaults, after asking; Undo takes them back as one step. A variant's
// kind goes first, which puts its own fields back with it.
async function resetGroup(group) {
  const count = group.querySelectorAll("input.changed, select.changed").length;
  const which = count === 1 ? "the changed setting" : `the ${count} changed settings`;
  if (!(await askConfirm(`Put ${which} of ${group.dataset.title} back to their defaults?`))) return;
  for (const select of group.querySelectorAll("select.kind.changed")) setControlValue(select, defaultValue(select));
  for (const control of group.querySelectorAll("input.changed, select.changed, input.invalid")) {
    setControlValue(control, defaultValue(control));
  }
  redrawEditors();
}

function flagAdvancedSummary(details) {
  const summary = details.querySelector(":scope > summary");
  // The fields only: the summary's own mark would keep it marked.
  summary.classList.toggle("changed", details.querySelector(":scope > .fields .changed") !== null);
}

// Find a setting: only the fields whose name or meaning holds every
// word typed show (a field in an editor's pane too: its row in the form
// comes back while searching), their groups and folds opened; the rest,
// and folds with none of them, are left out. "Show only the settings
// changed" keeps, of those, the ones changed from their defaults. Both
// off, every fold is as open as it was before.
let foldsBeforeFinding = null;

function applyFormFilter() {
  const words = findSetting.value.toLowerCase().replace(/_/g, " ").split(/\s+/).filter(Boolean);
  const filtering = words.length > 0 || changedOnly.checked;
  form.classList.toggle("filtering", filtering);
  const folds = [...form.querySelectorAll("details")];
  if (!filtering) {
    filterEmpty.hidden = true;
    if (foldsBeforeFinding) {
      for (const [fold, open] of foldsBeforeFinding) fold.open = open;
      foldsBeforeFinding = null;
    }
    return;
  }
  if (!foldsBeforeFinding) foldsBeforeFinding = new Map(folds.map((fold) => [fold, fold.open]));
  let matches = 0;
  for (const row of form.querySelectorAll(".field")) {
    const control = row.querySelector("input, select");
    const text = [
      row.querySelector("label")?.textContent,
      control?.dataset.name,
      row.title,
    ].join(" ").toLowerCase().replace(/_/g, " ");
    const match = words.every((word) => text.includes(word))
      && (!changedOnly.checked || row.querySelector(".changed") !== null);
    row.classList.toggle("match", match);
    if (match && !row.hidden) matches += 1;
  }
  for (const fold of folds) {
    const found = fold.querySelector(".field.match:not([hidden])") !== null;
    fold.classList.toggle("no-match", !found);
    fold.open = found;
  }
  filterEmpty.hidden = matches > 0;
  filterEmpty.textContent = changedOnly.checked && !words.length
    ? "No setting is changed from its default."
    : "No setting matches.";
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
  label.textContent = fieldLabel(field.name);
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
  } else if (field.type === "str") {
    input.type = "text";
    input.value = String(initial);
  } else {
    input.type = "text";
    input.value = field.type === "optional_float" && initial === null
      ? ""
      : JSON.stringify(initial);
    // Left empty, the value is worked out (the field's help says how).
    if (field.type === "optional_float") input.placeholder = "auto";
  }
  input.addEventListener("input", () => markChanged(input));
  input.addEventListener("change", () => input.classList.toggle("invalid", valueProblem(input) !== null));
  row.appendChild(label);
  // A random seed (body_engraving_seed) can be rerolled where it is.
  row.appendChild(field.name.endsWith("_seed") ? withReroll(input, input) : input);
  explain(row, field);
  return row;
}

// A new random seed (the pattern laid out afresh), as if typed.
function rerollSeed(input) {
  setControlValue(input, Math.floor(Math.random() * 100000) + 1);
}

// A seed's input with a Reroll button beside it, which rerolls the
// form's own field (``original``; the input itself, or its editor copy's).
function withReroll(input, original) {
  const holder = document.createElement("span");
  holder.className = "with-button";
  const button = document.createElement("button");
  button.type = "button";
  button.className = "secondary reroll";
  button.textContent = "Reroll";
  button.title = "A new random seed: the pattern laid out afresh";
  button.addEventListener("click", () => rerollSeed(original));
  holder.append(input, button);
  return holder;
}

// What the field means, from Python (webapp._field_help), shown on hover
// over its row; its name is marked as explained.
function explain(row, field) {
  if (!field.help) {
    row.title = field.name;
    return;
  }
  row.title = `${field.help}\n\n(${field.name})`;
  row.querySelector("label")?.classList.add("explained");
}

// A field's meaning shown under it while it is being set (its hover
// text: for a touch screen, and help too long to hover over), in the form
// or an editor's Settings; gone when the focus leaves the fields. A field
// changed from its default also shows the default there, with a button
// that puts it back.
const fieldHint = document.createElement("p");
fieldHint.className = "field-hint";
const FIELD_CONTROLS = "#form input, #form select, .editor-options input, .editor-options select";

function showFieldHint(control) {
  const inEditor = control.closest(".editor-options");
  const text = inEditor ? control.title : control.closest(".field")?.title;
  if (!text) {
    fieldHint.remove();
    return;
  }
  fieldHint.replaceChildren(text);
  if (control.classList.contains("invalid")) {
    const line = document.createElement("span");
    line.className = "hint-problem";
    line.textContent = valueProblem(control);
    fieldHint.append(line);
  }
  if (control.classList.contains("changed")) fieldHint.append(defaultLine(control));
  if (inEditor) (control.closest(".with-button") || control).after(fieldHint);
  else control.closest(".field").after(fieldHint);
}

// "Default: 44 [Reset to default]" for a changed field (an editor's copy
// reads its form field's default, and passes the reset on as any change).
function defaultLine(control) {
  const original = [...mirrors].find(([, copy]) => copy === control)?.[0] || control;
  const value = defaultValue(original);
  const line = document.createElement("span");
  line.className = "hint-default";
  let shown = defaultText(original, value);
  if (shown.length > 60) shown = shown.slice(0, 59) + "…";
  const button = document.createElement("button");
  button.type = "button";
  button.className = "secondary";
  button.textContent = "Reset to default";
  // Pressed, it leaves the focus in the field, so the hint stays.
  button.addEventListener("mousedown", (event) => event.preventDefault());
  button.addEventListener("click", () => {
    setControlValue(control, value);
    control.focus();
    showFieldHint(control);
  });
  line.append(`Default: ${shown}`, button);
  return line;
}

// A field's default value: a variant's kind keeps it on its holder.
function defaultValue(control) {
  if (control.matches("select.kind")) return control.closest(".variant").dataset.defaultKind;
  return JSON.parse(control.dataset.default);
}

// A default as its field shows it: a choice by its label, a checkbox on
// or off, an empty optional value "auto".
function defaultText(control, value) {
  if (control.tagName === "SELECT") {
    return [...control.options].find((option) => option.value === value)?.textContent ?? String(value);
  }
  const type = control.dataset.type;
  if (type === "bool") return value ? "on" : "off";
  if (type === "optional_float" && value === null) return "auto";
  if (type === "str") return value === "" ? "empty" : value;
  if (type === "float" || type === "int") return String(value);
  return JSON.stringify(value);
}

document.addEventListener("focusin", (event) => {
  const control = event.target;
  if (!(control instanceof Element) || !control.matches(FIELD_CONTROLS)) return;
  showFieldHint(control);
});
// Changed (or back to its default) as it is set, the hint follows.
for (const type of ["input", "change"]) {
  document.addEventListener(type, (event) => {
    const control = event.target;
    if (control === document.activeElement && control.matches?.(FIELD_CONTROLS)) showFieldHint(control);
  });
}
document.addEventListener("focusout", () => {
  setTimeout(() => {
    const focused = document.activeElement;
    if (!focused?.matches(FIELD_CONTROLS) && !fieldHint.contains(focused)) fieldHint.remove();
  }, 0);
});

// The wheel over a selected number field scrolls the page, as it does
// everywhere else, and leaves the value alone: the browser would step it
// a notch at a time, unseen. (Listened to on the field itself once it is
// selected, so the rest of the page scrolls unhindered.)
function scrollPastNumber(event) {
  const control = event.currentTarget;
  if (control !== document.activeElement || event.ctrlKey || event.metaKey) return;
  event.preventDefault();
  const scroller = scrollerOf(control);
  const unit = event.deltaMode === WheelEvent.DOM_DELTA_LINE ? 16
    : event.deltaMode === WheelEvent.DOM_DELTA_PAGE ? scroller.clientHeight : 1;
  scroller.scrollBy(event.deltaX * unit, event.deltaY * unit);
}

// The nearest box around an element that scrolls (a column of its own on
// a wide screen), or the page.
function scrollerOf(element) {
  for (let node = element.parentElement; node; node = node.parentElement) {
    if (/auto|scroll/.test(getComputedStyle(node).overflowY) && node.scrollHeight > node.clientHeight) return node;
  }
  return document.scrollingElement;
}

document.addEventListener("focusin", (event) => {
  const control = event.target;
  if (control instanceof HTMLInputElement && control.type === "number") {
    control.addEventListener("wheel", scrollPastNumber, { passive: false });
  }
});

// In a number field the arrow keys step by 1 as ever, by 10 with Shift
// and by 0.1 with Alt/Option (a whole-number field by 1).
document.addEventListener("keydown", (event) => {
  const control = event.target;
  if (!(control instanceof HTMLInputElement) || control.type !== "number") return;
  if (!(event.key === "ArrowUp" || event.key === "ArrowDown") || !(event.shiftKey || event.altKey)) return;
  if (event.ctrlKey || event.metaKey) return;
  const value = parseFloat(control.value);
  if (Number.isNaN(value)) return;
  const whole = control.dataset.type === "int";
  const step = event.shiftKey ? 10 : whole ? 1 : 0.1;
  event.preventDefault();
  // Rounded, so that 0.1 steps add up to 44.3, not 44.300000000000004.
  setControlValue(control, parseFloat((value + (event.key === "ArrowUp" ? step : -step)).toFixed(6)));
});

// A field's name in words: "body_pickup_frame_direction" reads "Pickup
// frame direction" (the body's own fields drop their "body_"); its name
// in the code, saved designs and help stays on hover and finds it too.
function fieldLabel(name) {
  const words = name.replace(/^body_/, "").replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

function renderChoiceField(set, field) {
  const row = document.createElement("div");
  row.className = "field";
  const label = document.createElement("label");
  label.textContent = fieldLabel(field.name);
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
  explain(row, field);
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
  label.textContent = fieldLabel(field.name);
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
  explain(row, field);
  // With a single kind (the body, always drawn) there is nothing to choose.
  row.hidden = Object.keys(field.variants).length < 2;
  holder.appendChild(row);
  const sub = document.createElement("div");
  sub.className = "subfields";
  holder.appendChild(sub);

  const renderSubfields = (kind, values) => {
    sub.innerHTML = "";
    // The instrument's own variant is its fields' default (a drawn body's
    // template outline and placements, a five-string bass's hardtail), so
    // a design loaded with those values shows nothing changed.
    const baseline = kind === field.default.kind ? field.default : {};
    const subfields = field.variants[kind].fields.map((subfield) => {
      const own = subfield.name in baseline ? { ...subfield, default: baseline[subfield.name] } : subfield;
      return values && subfield.name in values ? { ...own, value: values[subfield.name] } : own;
    });
    renderFieldList(set + "." + field.name, subfields, sub, row.hidden ? field.name : undefined);
    select.classList.toggle("changed", kind !== field.default.kind);
    if (field.name === "body_shape") bodyEditor.sync(kind, sub);
  };
  renderSubfields(field.default.kind, field.default);
  select.addEventListener("change", () => {
    renderSubfields(select.value, null);
    syncStringCount(holder);
  });
  return holder;
}

// A field changed from its default is marked. One whose value cannot be
// read (not a number, broken JSON) is marked invalid once it is given (a
// change: Enter, or leaving it), not while it is still being typed, and
// keeps its changed mark until it reads again.
function markChanged(input) {
  if (valueProblem(input)) return;
  input.classList.remove("invalid");
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
  if (type === "str") return input.value;
  return JSON.parse(input.value);
}

// A value that cannot be read, with the field it is in.
class FieldError extends Error {
  constructor(message, field) {
    super(message);
    this.field = field;
  }
}

// Why a field's value cannot be read, or null when it can.
function valueProblem(input) {
  let value;
  try {
    value = readValue(input);
  } catch (error) {
    return `Not valid JSON (${error.message})`;
  }
  if (typeof value !== "number" || !Number.isNaN(value)) return null;
  return input.validity.badInput || input.value.trim() !== "" ? "Not a number" : "Needs a number";
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
    const problem = valueProblem(input);
    if (problem) throw new FieldError(`${fieldLabel(input.dataset.name)} (${input.dataset.name}): ${problem}`, input);
    assign(input.dataset.set, input.dataset.name, readValue(input));
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

// The values the result on the page was built from: when the design has
// changed since, the result says so, with a button to build again.
let builtFrom = null;

function markStale() {
  document.getElementById("output-stale").hidden = !builtFrom || undoHistory.current === builtFrom;
}

// The tab's title is the guitar's name, with "Building…" in front while
// it builds; a build that ends out of sight (another tab in front) says
// there how it went until the page is seen again.
let titleNote = "";

function syncTitle() {
  document.title = [titleNote, guitarName.value.trim(), "CNCguitarwizard"].filter(Boolean).join(" — ");
}

function noteInTitle(note) {
  titleNote = note;
  syncTitle();
}
document.addEventListener("visibilitychange", () => {
  if (!document.hidden && !buildButton.classList.contains("busy")) noteInTitle("");
});
syncTitle();

async function build() {
  endTour();  // the tour ends at Build
  clearError();
  let payload;
  try {
    payload = collectValues();
  } catch (error) {
    // Built before the value was given (Ctrl/Cmd+Enter while typing): it
    // is marked now.
    error.field?.classList.add("invalid");
    showError(error.message, error.field);
    return;
  }
  buildButton.disabled = true;
  buildButton.classList.add("busy");
  buildButton.textContent = "Building…";
  setStatus("Building…");
  noteInTitle("Building…");
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
    builtFrom = JSON.stringify(payload);
    markStale();
    bringIntoView(output);
    const seconds = ((performance.now() - started) / 1000).toFixed(1);
    setStatus(`Built in ${seconds} s`, "ok");
  } catch (error) {
    console.error(error);
    showError("Build failed:\n" + error);
    setStatus("Build failed", "bad");
  } finally {
    buildButton.disabled = false;
    buildButton.classList.remove("busy");
    buildButton.textContent = "Build 3D and CNC files";
    setTimeout(() => progress.classList.add("hidden"), 1500);
    const built = status.className === "ok";
    noteInTitle(document.hidden ? (built ? "✓ Built" : "✗ Build failed") : "");
  }
}

function showResult(result) {
  for (const url of blobUrls) URL.revokeObjectURL(url);
  blobUrls = [];
  intro.classList.add("hidden");
  output.classList.remove("hidden");

  document.getElementById("plan").innerHTML = result.plan_view;
  zoomablePlot(document.getElementById("plan"));

  // One fold per part, the model and report first: each program numbered
  // in the order it is run, its toolpath plot a link on its row. The
  // folds start closed (Download all NC files has every program).
  const files = document.getElementById("files");
  files.innerHTML = "";
  const gcode = result.report.gcode;
  const isProgram = (name) => /\.k?nc$/.test(name);
  const stemOf = (name) => name.replace(/\.(nc|knc|svg)$/, "");
  const programOf = (name) => (/\.(nc|knc|svg)$/.test(name) ? gcode[stemOf(name)] : undefined);
  // build.json lists the programs alphabetically: order by part, then step.
  const partOrder = ["Model and report", "Body", "Wing bass", "Wing treble", "Neck", "Fretboard", "Inlays", "Nut jig", "Covers"];
  const groups = new Map(partOrder.map((part) => [part, []]));
  for (const info of Object.values(gcode)) if (!groups.has(info.part)) groups.set(info.part, []);
  for (const name of Object.keys(result.files)) {
    const info = programOf(name);
    groups.get(info ? info.part : "Model and report").push(name);
  }
  const rank = (name) => programOf(name)?.step ?? 0;
  const titles = {
    Body: "Body — top face up first, then flipped onto the dowels",
    "Wing bass": "Bass wing — from its own blank, glued to the neck-through block",
    "Wing treble": "Treble wing — from its own blank, glued to the neck-through block",
    Neck: "Neck",
    Fretboard: "Fretboard",
    Inlays: "Inlays — the marker pieces, cut from sheet to fit the pockets",
    "Nut jig": "Nut jig — a comb for filing the nut's slots, cut from sheet",
    Covers: "Covers — cut from sheet, in any order",
  };
  for (const [part, members] of groups) {
    if (!members.length) continue;
    const programCount = members.filter(isProgram).length;
    const fold = document.createElement("details");
    fold.className = "file-part";
    const head = document.createElement("summary");
    head.textContent = titles[part] || part;
    const count = document.createElement("span");
    count.className = "note";
    count.textContent = programCount
      ? ` — ${programCount} program${programCount === 1 ? "" : "s"}`
      : ` — ${members.length} file${members.length === 1 ? "" : "s"}`;
    head.appendChild(count);
    fold.appendChild(head);
    const table = document.createElement("table");
    fold.appendChild(table);
    files.appendChild(fold);
    // A program's plot goes on its own row, not one of its own.
    const plots = new Set(members.filter(isProgram).map((name) => `${stemOf(name)}.svg`));
    for (const name of members.filter((n) => !plots.has(n)).sort((a, b) => rank(a) - rank(b))) {
      addFile(name, table, plots.has(`${stemOf(name)}.svg`) ? `${stemOf(name)}.svg` : null);
    }
  }

  // The toolpath plots one at a time, chosen from a list by part, each
  // program by its step (the body's top first), or stepped through with
  // the arrows beside it.
  const tabs = document.getElementById("tabs");
  const toolpath = document.getElementById("toolpath");
  tabs.innerHTML = "";
  toolpath.innerHTML = "";
  const chooser = document.createElement("select");
  chooser.id = "toolpath-choice";
  chooser.setAttribute("aria-label", "Toolpath plot");
  for (const [part, members] of groups) {
    const plots = members.filter((name) => name.endsWith(".svg")).sort((a, b) => rank(a) - rank(b));
    if (!plots.length) continue;
    const group = document.createElement("optgroup");
    group.label = part;
    for (const name of plots) {
      const option = document.createElement("option");
      option.value = name;
      const step = programOf(name)?.step;
      option.textContent = `${step ? `${step}. ` : ""}${stemOf(name)}`;
      group.appendChild(option);
    }
    chooser.appendChild(group);
  }
  const show = () => {
    toolpath.innerHTML = result.files[chooser.value] || "";
    zoomablePlot(toolpath);
  };
  chooser.addEventListener("change", show);
  const stepper = (label, title, by) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary";
    button.textContent = label;
    button.title = title;
    button.addEventListener("click", () => {
      const count = chooser.options.length;
      if (!count) return;
      chooser.selectedIndex = (chooser.selectedIndex + by + count) % count;
      show();
    });
    return button;
  };
  tabs.append(stepper("‹", "The plot before", -1), chooser, stepper("›", "The next plot", 1));
  const first = ["Body_top.svg", "Neck_block_top.svg", "Neck_body_top.svg"].find((name) => name in result.files);
  if (first) chooser.value = first;
  show();

  function download(name, label) {
    const text = result.files[name];
    const type = name.endsWith(".svg") ? "image/svg+xml"
      : name.endsWith(".json") ? "application/json"
      : name.endsWith(".dxf") ? "application/dxf" : "text/plain";
    const url = URL.createObjectURL(new Blob([text], { type }));
    blobUrls.push(url);
    const link = document.createElement("a");
    link.className = "download";
    link.href = url;
    link.download = name;
    link.textContent = label;
    return link;
  }

  function addFile(name, table, plot) {
    const text = result.files[name];
    const info = programOf(name);
    const row = document.createElement("tr");
    row.innerHTML =
      `<td class="step">${info && isProgram(name) ? `${info.step}.` : ""}</td><td>${name}</td>` +
      `<td>${(text.length / 1024).toFixed(0)} kB</td><td class="links"></td>`;
    const links = row.lastElementChild;
    links.appendChild(download(name, "Download"));
    if (plot) {
      const link = download(plot, "Plot");
      link.title = `${plot}: the toolpaths drawn over the part`;
      links.appendChild(link);
    }
    if (isProgram(name)) {
      const button = document.createElement("button");
      button.className = "simulate";
      button.textContent = "Simulate";
      button.title = "Copy this program to the clipboard and open NC Viewer below";
      button.addEventListener("click", () => simulate(name, text));
      links.appendChild(button);
    }
    table.appendChild(row);
  }

  const summary = document.getElementById("summary");
  const report = result.report;
  const rows = [];
  for (const [part, stock] of Object.entries(report.stock)) {
    const pins = stock.index_pins_machine_xy;
    const where = pins.length ? `, pins at machine X ${pins.map((p) => p[0]).join(" / ")}` : "";
    rows.push([`${part} blank`, `${stock.length_mm} × ${stock.width_mm} × ${stock.thickness_mm} mm${where}`]);
    // A bought fretboard blank glued on a carrier that takes the pins.
    const carrier = stock.carrier;
    if (carrier) {
      rows.push([`${part} carrier`, `${carrier.length_mm} × ${carrier.width_mm} × ${carrier.thickness_mm} mm under the blank, reaching ${carrier.past_nut_end_mm} mm past its nut end and ${carrier.past_far_end_mm} mm past its far end; the pins go through it`]);
    }
    // A neck blank can be the neck's own plank with a block glued under
    // the headstock end once the neck is cut (neck_blank "laminated").
    const block = stock.laminated && stock.laminated.headstock_block_mm;
    if (block) {
      const glued = `${block.length} × ${block.width} × ${block.thickness} mm block under the headstock, from ${block.from_nut} mm behind the nut to past the tip`;
      rows.push(stock.blank === "laminated"
        ? [`${part} blank (laminated)`, `${stock.length_mm} × ${stock.width_mm} × ${stock.laminated.plank_thickness_mm} mm plank first; after ${report.gcode.Neck_back ? "Neck_back" : "Neck_back_finish"} glue a ${glued}, then the Headstock_ programs and the outline`]
        : [`${part} blank, or laminated`, `${stock.length_mm} × ${stock.width_mm} × ${stock.laminated.plank_thickness_mm} mm plank + ${glued} (neck_blank "laminated": the headstock in programs of its own)`]);
    }
  }
  const partRank = (part) => (partOrder.includes(part) ? partOrder.indexOf(part) : partOrder.length);
  const programs = Object.entries(report.gcode).sort(([, a], [, b]) => (
    partRank(a.part) - partRank(b.part) || a.step - b.step
  ));
  // The programs in one line: how many and how long; each one's tool and
  // time in a fold below the summary.
  const minutes = programs.reduce((total, [, info]) => total + info.estimated_minutes, 0);
  const hours = Math.floor(minutes / 60);
  const time = hours ? `${hours} h ${Math.round(minutes - 60 * hours)} min` : `${Math.round(minutes)} min`;
  rows.push(["Programs", `${programs.length}, about ${time} at the set feeds`]);
  const perProgram = document.querySelector("#summary-programs table");
  perProgram.innerHTML = programs.map(([name, info]) => (
    `<tr><th>${info.step}. ${name}</th><td>${info.tool}: ${info.estimated_minutes} min, ` +
    `${(info.cutting_length_mm / 1000).toFixed(1)} m of cutting, ${info.operations.length} operations</td></tr>`
  )).join("");
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

// ``after``: the element the panel shows under — the downloads table, or
// the body editor's own list of a single feature's files (the results,
// and so the table, may still be hidden before the first build).
async function simulate(name, text, after = document.getElementById("files")) {
  const panel = simulatorPanel();
  if (panel.previousElementSibling !== after) after.after(panel);
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
    name: guitarName.value.trim(),
    instrument,
    prototype,
    machining: values.machining,
  };
}

// Download every NC program of the last build in one ZIP, named for the
// guitar (Python packs it: webapp.nc_archive).
async function downloadNcZip() {
  ncZipButton.disabled = true;
  try {
    pyodide.globals.set("guitar_name", guitarName.value);
    const archive = await runPython(
      "import json\nfrom cncguitarwizard.webapp import nc_archive\n" +
      "json.dumps(nc_archive(guitar_name))"
    );
    if (archive.error) {
      showError(archive.error);
      return;
    }
    const bytes = Uint8Array.from(atob(archive.data), (c) => c.charCodeAt(0));
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([bytes], { type: "application/zip" }));
    link.download = archive.name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    setStatus(`Saved ${archive.name}`, "ok");
  } catch (error) {
    showError(`Cannot make the ZIP: ${error}`);
  } finally {
    ncZipButton.disabled = false;
  }
}

// A file name from the guitar's name, as Python makes the ZIP's.
function fileStem(name) {
  return name.trim().replace(/[^\p{L}\p{N}_ .-]+/gu, "-").replace(/[\s-]*-[\s-]*/g, "-")
    .replace(/^[ .-]+|[ .-]+$/g, "").slice(0, 80);
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
  const stem = fileStem(guitarName.value);
  link.download = stem
    ? `${stem}.json`
    : `cncguitarwizard-${design.instrument}-${design.saved.slice(0, 10)}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  setStatus(`Saved ${link.download}`, "ok");
  markSaved();
}

// An editor's outline as an SVG template to draw in another program, and
// read back from one (webapp.outline_template / import_outline): the
// body's, the headstock's or the inlay marker's.
const outlineFile = document.getElementById("outline-file");

function outlineEditor(part) {
  return { body: bodyEditor, headstock: headstockEditor, inlay: inlayEditor }[part];
}

async function exportOutline(part, kind = "svg") {
  const editor = outlineEditor(part);
  if (!pyodide) return;
  let payload;
  try {
    payload = collectValues();
  } catch (error) {
    editor.setStatus(`Cannot export the outline: ${error.message}`, "bad");
    return;
  }
  pyodide.globals.set("payload_json", JSON.stringify(payload));
  pyodide.globals.set("outline_part", part);
  pyodide.globals.set("outline_kind", kind);
  const result = await runPython(
    "import json\nfrom cncguitarwizard.webapp import outline_template\n" +
    "json.dumps(outline_template(json.loads(payload_json), outline_part, outline_kind))"
  );
  if (result.error) {
    editor.setStatus(`Cannot export the outline: ${result.error}`, "bad");
    return;
  }
  const link = document.createElement("a");
  const type = kind === "dxf" ? "application/dxf" : "image/svg+xml";
  link.href = URL.createObjectURL(new Blob([result[kind]], { type }));
  link.download = `${fileStem(guitarName.value) || "cncguitarwizard"}-${part}-outline.${kind}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  editor.setStatus(kind === "dxf"
    ? `Saved ${link.download}: edit the outline on layer cgwOutline, keep the red marks (cgwMarkA–C), then Import DXF.`
    : `Saved ${link.download}: edit the black outline, keep the red marks, then Import SVG.`, "ok");
}

async function importOutline(part, file) {
  const editor = outlineEditor(part);
  if (!pyodide || !editor.layout) return;
  let payload;
  try {
    payload = collectValues();
  } catch (error) {
    editor.setStatus(`Cannot import ${file.name}: ${error.message}`, "bad");
    return;
  }
  pyodide.globals.set("payload_json", JSON.stringify(payload));
  pyodide.globals.set("outline_part", part);
  pyodide.globals.set("outline_svg", await file.text());
  const result = await runPython(
    "import json\nfrom cncguitarwizard.webapp import import_outline\n" +
    "json.dumps(import_outline(json.loads(payload_json), outline_part, outline_svg))"
  );
  if (result.error) {
    editor.setStatus(`Cannot import ${file.name}: ${result.error}`, "bad");
    return;
  }
  const values = result.values;
  if (part === "body") {
    bodyEditor.points = values.control_points;
    // A pattern drawn in the template's Pattern layer: the engraving's
    // fields (drawn lines, or none), set as if chosen in the form.
    for (const [name, value] of Object.entries(values)) {
      if (name === "control_points") continue;
      const control = form.querySelector(`[data-set="prototype"][data-name="${name}"]`);
      if (control) setControlValue(control, value);
    }
  } else if (part === "headstock") {
    headstockEditor.edges = { bass: values.headstock_bass_edge, treble: values.headstock_treble_edge };
    headstockEditor.tip = values.headstock_tip_points;
    // Lines drawn on the face (or none), set as if typed in the form.
    if (values.headstock_engraving_lines) {
      setControlValue(form.querySelector('[data-set="prototype"][data-name="headstock_engraving_lines"]'),
        values.headstock_engraving_lines);
    }
  } else {
    // Its corners, a drawn marker from now on (commit sets the style).
    inlayEditor.points = values.inlay_points;
  }
  // One change to undo; the drawing then says what still does not fit,
  // after what the import made of the file.
  editor.commit();
  editor.notice = result.message;
  editor.draw();
}

// An editor's status: what an import made (its notice, kept until the
// next change in the editor) on a line of its own, then how the drawing
// stands — what does not fit in red and bold.
function showEditorStatus(editor, text, kind) {
  editor.status.className = "note editor-status";
  editor.status.replaceChildren();
  if (editor.notice) {
    const notice = document.createElement("span");
    notice.className = "status-notice";
    notice.textContent = editor.notice;
    editor.status.appendChild(notice);
  }
  const message = document.createElement("span");
  message.className = `status-message ${kind || ""}`.trim();
  message.textContent = text;
  editor.status.appendChild(message);
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
  else if (type === "str") control.value = String(value);
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

// The design as the page was last left, kept in this browser: saved after
// every settled change (and the guitar's name), put back on loading. A
// design that cannot be put back is passed over; Reset starts afresh.
const LAST_DESIGN = "cncguitarwizard.lastDesign";
let autosaveReady = false;

function autosave() {
  if (!autosaveReady) return;
  try {
    localStorage.setItem(LAST_DESIGN, JSON.stringify(designDocument()));
  } catch {
    // No storage (a private window, or full), or a field mid-edit.
  }
}

function restoreLastDesign() {
  let text = null;
  try {
    text = localStorage.getItem(LAST_DESIGN);
  } catch {
    return false;
  }
  if (!text) return false;
  try {
    applyDesign(JSON.parse(text));
    return true;
  } catch (error) {
    console.warn("The last design could not be put back:", error);
    return false;
  }
}

function applyDesign(design) {
  if (!design || design.format !== DESIGN_FORMAT) {
    throw new Error("This is not a CNCguitarwizard design file.");
  }
  if (!(design.instrument in schema.instruments)) {
    throw new Error(`Unknown instrument ${JSON.stringify(design.instrument)}.`);
  }
  // An older design's outdated values are brought up to date first
  // (webapp.upgrade_design).
  pyodide.globals.set("design_json", JSON.stringify(design));
  design = JSON.parse(pyodide.runPython(
    "import json\nfrom cncguitarwizard.webapp import upgrade_design\n" +
    "json.dumps(upgrade_design(json.loads(design_json)))"
  ));
  instrumentSelect.value = design.instrument;
  instrumentSelect.dataset.current = design.instrument;
  guitarName.value = typeof design.name === "string" ? design.name : "";
  syncTitle();
  renderForm();
  const unknown = [
    ...applyValues("prototype", design.prototype),
    ...applyValues("machining", design.machining),
  ];
  applyStringLimits();
  headstockEditor.sync();
  inlayEditor.scheduleRefresh();
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
    markSaved();
    if (unknown.length) {
      showError(`Loaded ${file.name}, but skipped settings this version does not have: ${unknown.join(", ")}.`);
    }
  } catch (error) {
    showError(`Cannot load ${file.name}: ${error.message}`);
  }
}

// ---------------------------------------------------------------------------
// Undo and redo: the design's values are kept after every change — a drag,
// a template or a removal in an editor, a field changed in the form, a
// reset, an instrument switch or a loaded design — so each can be stepped
// back and forward again. One history serves the whole page: the Undo and
// Redo buttons (beside Reset and in each editor's pane) and Ctrl/Cmd+Z,
// Ctrl/Cmd+Shift+Z or Ctrl+Y step through it.

const HISTORY_LIMIT = 100;

// Values put in from outside the editors (an undo, a group's reset): the
// editors redraw from the form.
function redrawEditors() {
  applyStringLimits();
  syncMirrors();
  headstockEditor.sync();
  inlayEditor.scheduleRefresh();
  bodyEditor.reloadPoints();
  bodyEditor.scheduleRefresh();
}

const undoHistory = {
  undo: [],       // the values before each change (JSON), the latest last
  redo: [],
  current: null,  // the values as they are
  timer: null,
  restoring: false,
  pointerDown: false,

  snapshot() {
    try {
      return JSON.stringify(collectValues());
    } catch (error) {
      return null;  // a field still being typed
    }
  },

  // Start afresh on the form just drawn.
  start() {
    this.undo = [];
    this.redo = [];
    this.current = this.snapshot();
    this.update();
  },

  // Values may have changed: keep them once things settle (a drag ended,
  // a load or a template has put all its values in).
  note() {
    if (this.restoring) return;
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this.flush(), 300);
  },

  flush() {
    clearTimeout(this.timer);
    this.timer = null;
    if (this.restoring || this.current === null) return;
    if (this.pointerDown) {
      this.note();
      return;
    }
    const now = this.snapshot();
    if (now === null || now === this.current) return;
    this.undo.push(this.current);
    if (this.undo.length > HISTORY_LIMIT) this.undo.shift();
    this.redo = [];
    this.current = now;
    this.update();
  },

  undoStep() {
    this.flush();
    if (!this.undo.length) return;
    this.redo.push(this.current);
    this.restore(this.undo.pop());
  },

  redoStep() {
    this.flush();
    if (!this.redo.length) return;
    this.undo.push(this.current);
    this.restore(this.redo.pop());
  },

  // Put kept values back: only those that differ, as a loaded design's
  // are (another instrument's form drawn first), and redraw the editors.
  restore(json) {
    const target = JSON.parse(json);
    const { instrument, ...prototype } = target.prototype;
    this.restoring = true;
    try {
      if (instrument !== instrumentSelect.value) {
        instrumentSelect.value = instrument;
        instrumentSelect.dataset.current = instrument;
        renderForm();
      }
      let now = null;
      try {
        now = collectValues();
      } catch (error) {
        // A field mid-edit: every value goes back.
      }
      const differing = (set, values) => Object.fromEntries(Object.entries(values).filter(
        ([name, value]) => !now || JSON.stringify(value) !== JSON.stringify(now[set][name])
      ));
      applyValues("prototype", differing("prototype", prototype));
      applyValues("machining", differing("machining", target.machining));
      redrawEditors();
    } finally {
      this.restoring = false;
      clearTimeout(this.timer);
    }
    this.current = this.snapshot() || json;
    this.update();
  },

  // The fields a kept step differs from the values now in, named as the
  // form labels them (a variant's own fields after it: "Bridge · String
  // spacing"), for the buttons' tooltips.
  changes(json) {
    const kept = JSON.parse(json), now = JSON.parse(this.current);
    const names = [];
    for (const set of ["prototype", "machining"]) {
      for (const name of new Set([...Object.keys(kept[set]), ...Object.keys(now[set])])) {
        const a = kept[set][name], b = now[set][name];
        if (JSON.stringify(a) === JSON.stringify(b)) continue;
        if (a && b && typeof a === "object" && a.kind !== undefined && a.kind === b.kind) {
          for (const sub of Object.keys(a)) {
            if (JSON.stringify(a[sub]) !== JSON.stringify(b[sub])) names.push(`${fieldLabel(name)} · ${fieldLabel(sub)}`);
          }
        } else {
          names.push(fieldLabel(name));
        }
      }
    }
    if (names.length > 4) return `${names.slice(0, 4).join(", ")} and ${names.length - 4} more`;
    return names.join(", ") || "the last change";
  },

  update() {
    const label = (stack) => (stack.length ? this.changes(stack[stack.length - 1]) : "");
    const undone = label(this.undo), redone = label(this.redo);
    for (const button of document.querySelectorAll(".undo-button")) {
      button.disabled = !this.undo.length;
      button.title = undone ? `Undo: ${undone} (Ctrl/Cmd+Z)` : "Nothing to undo";
    }
    for (const button of document.querySelectorAll(".redo-button")) {
      button.disabled = !this.redo.length;
      button.title = redone ? `Redo: ${redone} (Ctrl/Cmd+Shift+Z)` : "Nothing to redo";
    }
    autosave();
    markStale();
    countChanged();
    markUnsaved();
  },
};
guitarName.addEventListener("input", () => {
  autosave();
  syncTitle();
  markUnsaved();
});

// Save design is marked while the design differs from the one last saved
// or loaded in this browser (kept there, so that a reload still knows
// it); with none saved or loaded yet, once a setting is changed or the
// guitar named.
const SAVED_DESIGN = "cncguitarwizard.savedDesign";
const saveDesignTitle = saveDesignButton.title;
let savedDesign = null;
try {
  savedDesign = localStorage.getItem(SAVED_DESIGN);
} catch {
  // No storage: what this page saves or loads is still remembered.
}

function designKey() {
  return `${guitarName.value.trim()}\n${undoHistory.current}`;
}

function markSaved() {
  undoHistory.flush();  // a change still settling is part of it
  savedDesign = designKey();
  try {
    localStorage.setItem(SAVED_DESIGN, savedDesign);
  } catch {
    // No storage: remembered until the page is left.
  }
  markUnsaved();
}

function markUnsaved() {
  if (undoHistory.current === null) return;  // a field mid-edit
  const unsaved = savedDesign === null
    ? form.querySelector(".changed") !== null || guitarName.value.trim() !== ""
    : designKey() !== savedDesign;
  saveDesignButton.classList.toggle("unsaved", unsaved);
  saveDesignButton.title = unsaved ? `${saveDesignTitle} · changed since last saved` : saveDesignTitle;
}

// A drag writes its values when it ends; until then nothing is kept.
window.addEventListener("pointerdown", () => { undoHistory.pointerDown = true; }, true);
for (const type of ["pointerup", "pointercancel"]) {
  window.addEventListener(type, () => { undoHistory.pointerDown = false; }, true);
}
form.addEventListener("change", () => undoHistory.note());
document.addEventListener("click", (event) => {
  if (event.target.closest(".undo-button")) undoHistory.undoStep();
  else if (event.target.closest(".redo-button")) undoHistory.redoStep();
});
// Ctrl/Cmd+Enter builds, from anywhere on the page (a field being typed
// in too: its value is read as it stands).
document.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" || !(event.ctrlKey || event.metaKey) || event.altKey) return;
  if (buildButton.disabled || document.querySelector("dialog[open]")) return;
  event.preventDefault();
  build();
});

// Ctrl/Cmd+S saves the design and Ctrl/Cmd+O opens one, as Save design
// and Load design do, in place of the browser's own saving and opening.
document.addEventListener("keydown", (event) => {
  if (!(event.ctrlKey || event.metaKey) || event.altKey || event.shiftKey) return;
  const key = event.key.toLowerCase();
  if (key !== "s" && key !== "o") return;
  event.preventDefault();
  if (document.querySelector("dialog[open]")) return;
  if (key === "s" && !saveDesignButton.disabled) saveDesign();
  if (key === "o" && !loadDesignButton.disabled) loadDesignFile.click();
});

document.addEventListener("keydown", (event) => {
  if (!(event.ctrlKey || event.metaKey) || event.altKey || !schema) return;
  const key = event.key.toLowerCase();
  const redo = (key === "z" && event.shiftKey) || (key === "y" && !event.shiftKey);
  if (!redo && !(key === "z" && !event.shiftKey)) return;
  // Text being typed keeps the browser's own undo.
  const target = event.target;
  const typing = target.isContentEditable || target.tagName === "TEXTAREA"
    || (target.tagName === "INPUT" && !["checkbox", "radio", "button", "file"].includes(target.type));
  if (typing || document.querySelector("dialog[open]")) return;
  event.preventDefault();
  if (redo) undoHistory.redoStep();
  else undoHistory.undoStep();
});

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

// An open curve through the points, both ends included: each end stands
// in for its own missing neighbour (as geometry.primitives.open_catmull_rom).
function openCatmullRom(points, samples) {
  const out = [];
  const n = points.length;
  const blend = (a, b, c, d, t) => 0.5 * (
    2 * b + (c - a) * t + (2 * a - 5 * b + 4 * c - d) * t * t
    + (3 * b - a - 3 * c + d) * t * t * t
  );
  for (let i = 0; i < n - 1; i++) {
    const p0 = points[Math.max(i - 1, 0)], p1 = points[i];
    const p2 = points[i + 1], p3 = points[Math.min(i + 2, n - 1)];
    for (let s = 0; s < samples; s++) {
      const t = s / samples;
      out.push([blend(p0[0], p1[0], p2[0], p3[0], t), blend(p0[1], p1[1], p2[1], p3[1], t)]);
    }
  }
  out.push(points[n - 1]);
  return out;
}

// The contour lines drawn in the body editor: where the arm contour (on
// the top) and the belly cut (on the back) start.
const CONTOUR_LINES = [
  { key: "arm", layout: "arm_contour", field: "arm_contour_points", label: "arm contour" },
  { key: "belly", layout: "belly_cut", field: "belly_cut_points", label: "belly cut" },
];

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
  upright: false,   // the drawing shown upright, the neck up (a view only)
  handles: [],
  refreshTimer: null,
  loaded: null,     // the template last loaded on this form
  shown: "",        // the template Start from shows (the drawing's)

  sync(kind, subfields) {
    // A new form (a reset, another instrument, a loaded design): no
    // template loaded on it yet.
    this.loaded = null;
    this.input = subfields.querySelector("input[data-name='control_points']");
    const active = kind === "your_design" && this.input !== null;
    this.panel.classList.toggle("hidden", !active);
    showMirroredRows();
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
    (parent || this.root || this.svg).appendChild(node);
    return node;
  },

  // Start a drawing: everything goes into one group, turned over (Y
  // mirrored) for a left-handed build, so the design, kept as drawn
  // (right-handed), shows as it is built; toModel reads points back
  // through the same group. The view box frames the model's Y range. The
  // body editor may show it upright (this.upright: turned a quarter
  // clockwise, the neck up), a view only: the other editors share this
  // and stay as they are.
  begin(mirrored, minX, minY, maxX, maxY) {
    this.svg.innerHTML = "";
    this.root = null;
    const transform = `${this.upright ? "rotate(90) " : ""}${mirrored ? "scale(1,-1)" : ""}`.trim();
    this.root = this.element("g", transform ? { transform } : {});
    const top = mirrored ? minY : -maxY;
    const width = maxX - minX, height = maxY - minY;
    this.baseBox = this.upright
      ? [-(top + height), minX, height, width]
      : [minX, top, width, height];
    // Zoomed in (see enableZoom), the same part of the drawing stays in view.
    const zoom = this.zoom;
    const box = zoom
      ? [zoom.cx - this.baseBox[2] / zoom.scale / 2, zoom.cy - this.baseBox[3] / zoom.scale / 2,
        this.baseBox[2] / zoom.scale, this.baseBox[3] / zoom.scale]
      : this.baseBox;
    this.svg.setAttribute("viewBox", box.join(" "));
    this.showZoom?.();  // a zoom let go of (a turn) lets its chip go too
  },

  // Upright or sideways (the default), as last chosen in this browser.
  turn(upright) {
    this.upright = upright;
    this.zoom = null;
    try {
      localStorage.setItem("cncguitarwizard.bodyUpright", upright ? "1" : "0");
    } catch {
      // No storage (a private window): the view is only for now.
    }
    const button = document.getElementById("body-editor-turn");
    button.textContent = upright ? "Turn sideways" : "Turn upright";
    button.title = upright
      ? "Lay the drawing on its side, the neck to the left (the view only)"
      : "Turn the drawing upright, the neck up (the view only)";
    if (this.layout) this.draw();
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
    // Frame everything: the outline plus the features on the body.
    const bodyFeatures = layout.polygons.filter((p) => p.role !== "neck");
    const all = [...this.outline(), ...bodyFeatures.flatMap((p) => p.points)];
    const xs = all.map((p) => p[0]), ys = all.map((p) => p[1]);
    const margin = 40;
    const minX = Math.min(...xs) - margin, maxX = Math.max(...xs) + margin;
    const minY = Math.min(...ys) - margin, maxY = Math.max(...ys) + margin;
    this.begin(layout.mirrored, minX, minY, maxX, maxY);

    const grid = this.element("g", { stroke: "#eee6d8", "stroke-width": 0.5 });
    for (let x = Math.ceil(minX / 50) * 50; x <= maxX; x += 50) {
      this.element("line", { x1: x, y1: -maxY, x2: x, y2: -minY }, grid);
    }
    for (let y = Math.ceil(minY / 50) * 50; y <= maxY; y += 50) {
      this.element("line", { x1: minX, y1: -y, x2: maxX, y2: -y }, grid);
    }
    this.element("line", { x1: minX, y1: 0, x2: maxX, y2: 0, stroke: "#bbb", "stroke-width": 0.5, "stroke-dasharray": "4,3" });

    this.outlinePath = this.element("path", { class: "outline", d: this.pathData(this.outline()) });
    // A neck-through's centre block: the strip between its glue lines,
    // within the outline (clipped to it, so it follows the outline's edits).
    this.blockClip = null;
    if (layout.neck_through) {
      const half = layout.neck_through.width / 2;
      const clip = this.element("clipPath", { id: "neck-through-clip" });
      this.blockClip = this.element("path", { d: this.pathData(this.outline()) }, clip);
      const block = this.element("rect", {
        x: minX, y: -half, width: maxX - minX, height: 2 * half,
        fill: "#e2cc9f", stroke: "#6b4a1f", "stroke-width": 0.6,
        "clip-path": "url(#neck-through-clip)", "pointer-events": "none",
      });
      this.element("title", {}, block).textContent = "Neck-through block: the wings are glued to its sides";
    }

    const styles = {
      neck: { fill: "#3b2a1a", "fill-opacity": 0.85, stroke: "none" },
      pocket: { fill: "#f2c4b3", "fill-opacity": 0.9, stroke: "#7a3a1a", "stroke-width": 0.5 },
      pickup: { fill: "#f2c4b3", stroke: "#7a3a1a", "stroke-width": 0.5 },
      bridge: { fill: "#f2c4b3", stroke: "#7a3a1a", "stroke-width": 0.5 },
      bridge_plate: { fill: "#d8d0c2", "fill-opacity": 0.5, stroke: "#6b625a", "stroke-width": 0.5, "stroke-dasharray": "2,2" },
      top_control: { fill: "#c9b7e6", "fill-opacity": 0.55, stroke: "#5a3a8a", "stroke-width": 0.6 },
      plateau: { fill: "none", stroke: "#8a6a3a", "stroke-width": 0.8, "stroke-dasharray": "6,3" },
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
    // No bore with the jack on a control plate (its hole is the plate's).
    const jack = layout.jack;
    if (jack) {
      const bore = this.element("line", { x1: jack.x, y1: -jack.y, x2: jack.x2, y2: -jack.y2, stroke: "#222", "stroke-width": jack.r * 2, "stroke-opacity": 0.25 }, features);
      place(bore, jack.group, "Output jack");
      if (jack.cup) {
        const cup = this.element("line", { x1: jack.x, y1: -jack.y, x2: jack.cup.x2, y2: -jack.cup.y2, stroke: "#222", "stroke-width": jack.cup.r * 2, "stroke-opacity": 0.2 }, features);
        place(cup, jack.group, "Output jack (cup)");
      }
      const socket = this.element("circle", { cx: jack.x, cy: -jack.y, r: jack.r, fill: "#fff", "fill-opacity": 0.6, stroke: "#222", "stroke-width": 0.8 }, features);
      place(socket, jack.group, "Output jack");
    }

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

    // The pickguard, over the features, with square handles at its
    // control points; dragging one draws the guard (pickguard_points).
    this.guardPoints = layout.pickguard ? layout.pickguard.points.map((p) => [...p]) : null;
    if (this.guardPoints) {
      // The guard with its openings and holes cut out of it (even-odd).
      this.guardPath = this.element("path", {
        d: this.guardData(), "fill-rule": "evenodd",
        fill: "#ffffff", "fill-opacity": 0.55, stroke: "#333", "stroke-width": 0.7,
        "stroke-dasharray": layout.pickguard.automatic ? "4,2" : "none", "pointer-events": "none",
      });
      // One click on its edge adds a point there.
      this.guardHit = this.element("path", { class: "outline-hit", d: this.pathData(closedCatmullRom(this.guardPoints, 8)) });
      // Dragging the edge moves the whole guard, or onto Create NC file
      // makes its programs; a click without a drag adds a point.
      this.guardHit.addEventListener("pointerdown", (event) => this.startGuardMove(event));
      this.guardHit.addEventListener("click", (event) => {
        if (event.detail <= 1 && !this.guardMoved) this.addGuardPoint(event);
      });
      this.element("title", {}, this.guardHit).textContent =
        "Click the pickguard's edge to add a point, drag it to move the guard (or onto Create NC file)";
      this.guardPoints.forEach((point, index) => {
        const handle = this.element("rect", { class: "guard-handle", x: point[0] - 2.5, y: -point[1] - 2.5, width: 5, height: 5 });
        this.element("title", {}, handle).textContent = "Pickguard point — drag to shape the guard, Alt-click or right-click to remove it";
        handle.addEventListener("pointerdown", (event) => {
          if (event.altKey) { this.removeGuardPoint(index); return; }
          this.startGuardDrag(event, index, handle);
        });
        handle.addEventListener("contextmenu", (event) => { event.preventDefault(); this.removeGuardPoint(index); });
      });
    }

    // The humbucker frames over the pickups, each with round handles at
    // its points; dragging one draws that pickup's frame
    // (body_<position>_frame_points), click its edge to add a point.
    this.frameHandles = (layout.frames || []).map((frame) => frame.handles.map((p) => [...p]));
    this.framePaths = [];
    this.frameHandleNodes = [];
    (layout.frames || []).forEach((frame, frameIndex) => {
      const path = this.element("path", {
        d: this.frameData(frameIndex), "fill-rule": "evenodd",
        fill: "#1b1b1b", "fill-opacity": 0.8, stroke: frame.problem ? "#c0392b" : "#000",
        "stroke-width": frame.problem ? 1.2 : 0.6, "pointer-events": "none",
      });
      this.framePaths.push(path);
      const hit = this.element("path", { class: "outline-hit", d: this.pathData(closedCatmullRom(this.frameHandles[frameIndex], 8)) });
      hit.addEventListener("click", (event) => this.addFramePoint(event, frameIndex));
      this.element("title", {}, hit).textContent =
        `The ${frame.position} pickup's frame${frame.turned ? " (turned round)" : ""} — click its edge to add a point`;
      this.frameHandles[frameIndex].forEach((point, index) => {
        const handle = this.element("circle", { class: "frame-handle", cx: point[0], cy: -point[1], r: 1.6 });
        this.frameHandleNodes.push(handle);
        this.element("title", {}, handle).textContent =
          `${frame.position[0].toUpperCase()}${frame.position.slice(1)} pickup frame point — drag to shape it, Alt-click or right-click to remove it`;
        handle.addEventListener("pointerdown", (event) => {
          if (event.altKey) { this.removeFramePoint(frameIndex, index); return; }
          this.startFrameDrag(event, frameIndex, index, handle);
        });
        handle.addEventListener("contextmenu", (event) => { event.preventDefault(); this.removeFramePoint(frameIndex, index); });
      });
    });

    // A stepped top's lines, straight between their points, with diamond
    // handles; dragging one draws the steps (step_points).
    this.stepPoints = layout.steps ? layout.steps.points.map((line) => line.map((p) => [...p])) : null;
    this.stepPaths = [];
    this.stepHandles = [];
    (this.stepPoints || []).forEach((line, lineIndex) => {
      this.stepPaths.push(this.element("path", {
        class: "step-line", d: this.pathData(line),
        "stroke-dasharray": layout.steps.automatic ? "4,2" : "none",
      }));
      const hit = this.element("path", { class: "outline-hit", d: this.pathData(line) });
      hit.addEventListener("click", (event) => this.addStepPoint(event, lineIndex));
      this.element("title", {}, hit).textContent = `Click step ${lineIndex + 1}'s line to add a point`;
      line.forEach((point, index) => {
        const handle = this.element("rect", {
          class: "step-handle", x: point[0] - 2, y: -point[1] - 2, width: 4, height: 4,
          transform: `rotate(45 ${point[0]} ${-point[1]})`,
        });
        this.element("title", {}, handle).textContent = `Step ${lineIndex + 1} point — drag to shape the step, Alt-click or right-click to remove it`;
        handle.addEventListener("pointerdown", (event) => {
          if (event.altKey) { this.removeStepPoint(lineIndex, index); return; }
          this.startStepDrag(event, lineIndex, index, handle);
        });
        handle.addEventListener("contextmenu", (event) => { event.preventDefault(); this.removeStepPoint(lineIndex, index); });
        this.stepHandles.push(handle);
      });
    });

    // The decorative engraving, drawn as the bit's centre lines; a
    // relief's shapes (camo) shaded darker the deeper they are cut, the
    // deeper over the shallower where they overlap (as they are cut).
    const deepest = Math.max(0, ...(layout.relief || []).map((shape) => shape.depth));
    for (const shape of [...(layout.relief || [])].sort((a, b) => a.depth - b.depth)) {
      const relief = this.element("path", {
        class: "relief", d: this.pathData(shape.outline), "fill-opacity": 0.15 + 0.6 * shape.depth / deepest,
      });
      this.element("title", {}, relief).textContent = `Relief shape, ${shape.depth} mm deep`;
    }
    for (const line of layout.engraving || []) {
      this.element("path", { class: "engraving", d: this.openPath(line) });
    }

    // The lines where the arm contour and the belly cut start, with
    // round handles at their control points; dragging one draws it
    // (arm_contour_points / belly_cut_points).
    this.contourLines = {};
    for (const spec of CONTOUR_LINES) {
      const data = layout[spec.layout];
      if (!data) continue;
      const line = { spec, points: data.points.map((p) => [...p]) };
      this.contourLines[spec.key] = line;
      const d = this.openPath(openCatmullRom(line.points, 8));
      line.path = this.element("path", {
        class: `contour-line ${spec.key}`, d,
        "stroke-dasharray": data.automatic ? "4,2" : "none",
      });
      line.hit = this.element("path", { class: "outline-hit", d });
      line.hit.addEventListener("click", (event) => {
        if (event.detail <= 1) this.addContourPoint(spec.key, event);
      });
      this.element("title", {}, line.hit).textContent = `Click the ${spec.label}'s line to add a point`;
      line.handles = line.points.map((point, index) => {
        const handle = this.element("circle", { class: `contour-handle ${spec.key}`, cx: point[0], cy: -point[1], r: 2.4 });
        this.element("title", {}, handle).textContent =
          `Where the ${spec.label} starts — drag to move, Alt-click or right-click to remove; the ends sit on the body's edge`;
        handle.addEventListener("pointerdown", (event) => {
          if (event.altKey) { this.removeContourPoint(spec.key, index); return; }
          this.startContourDrag(event, spec.key, index, handle);
        });
        handle.addEventListener("contextmenu", (event) => { event.preventDefault(); this.removeContourPoint(spec.key, index); });
        return handle;
      });
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
    // The contour lines' ends sit on the outline: their handles go on
    // top of the outline's click strip and handles, so they drag.
    for (const line of Object.values(this.contourLines)) {
      for (const handle of line.handles) handle.parentNode.appendChild(handle);
    }
    // The steps' handles go on top of everything: beside the neck pocket
    // they sit over its bolts and over each other's lines.
    for (const handle of this.stepHandles) handle.parentNode.appendChild(handle);
    // A frame's points too: near the neck and the body's edge they sit
    // over the outline's click strip and its handles.
    for (const handle of this.frameHandleNodes) handle.parentNode.appendChild(handle);
    this.check();
    this.showTemplate();
  },

  toModel(event) {
    const point = this.svg.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    const local = point.matrixTransform((this.root || this.svg).getScreenCTM().inverse());
    return [Math.round(local.x * 10) / 10, Math.round(-local.y * 10) / 10];
  },

  // A handle and the outline through it drawn where they are now, not yet
  // committed: a drag under way, or the tour showing one.
  showPoint(index, shown) {
    this.handles[index].setAttribute("cx", shown[0]);
    this.handles[index].setAttribute("cy", -shown[1]);
    const outline = this.pathData(this.outline());
    this.outlinePath.setAttribute("d", outline);
    if (this.blockClip) this.blockClip.setAttribute("d", outline);
    this.outlineHit.setAttribute("d", outline);
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
      this.showPoint(index, shown);
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
    const drop = document.getElementById("body-editor-nc");
    this.svg.classList.add("dragging");
    const overDrop = (event) => {
      const box = drop.getBoundingClientRect();
      return event.clientX >= box.left && event.clientX <= box.right
        && event.clientY >= box.top && event.clientY <= box.bottom;
    };
    const svgBox = this.svg.getBoundingClientRect();
    const inDrawing = (event) => event.clientX >= svgBox.left && event.clientX <= svgBox.right
      && event.clientY >= svgBox.top && event.clientY <= svgBox.bottom;
    const move = (moveEvent) => {
      const [x, y] = this.toModel(moveEvent);
      delta = [x - start[0], alongNeck ? 0 : y - start[1]];
      // Out of the drawing (on its way to Create NC file, say) a pickup
      // follows the pointer too; in it, it only slides along the neck.
      const shown = inDrawing(moveEvent) ? delta : [x - start[0], y - start[1]];
      for (const member of members) member.setAttribute("transform", `translate(${shown[0]} ${-shown[1]})`);
      drop.classList.toggle("over", overDrop(moveEvent));
    };
    const end = (endEvent) => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", end);
      window.removeEventListener("pointercancel", end);
      drop.classList.remove("over");
      this.svg.classList.remove("dragging");
      // Dropped on "Create NC file": the feature stays put and gets its
      // own programs instead.
      if (endEvent && overDrop(endEvent)) {
        for (const member of members) member.removeAttribute("transform");
        this.createNc(group);
        return;
      }
      if (delta[0] || delta[1]) {
        // Dropped wholly outside the body: offer to remove it instead.
        const removal = this.leftBody(group, delta) ? this.removal(group) : null;
        if (removal) {
          askConfirm(`Remove ${removal.label}?`).then((yes) => {
            if (yes) {
              removal.apply();
              this.refresh();
            } else {
              for (const member of members) member.removeAttribute("transform");
            }
          });
          return;
        }
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

  // Drag one pickguard point; on drop the guard's points are written
  // (drawn from now on: Auto pickguard goes back to the automatic one).
  startGuardDrag(event, index, handle) {
    event.preventDefault();
    event.stopPropagation();
    handle.classList.add("dragging");
    const move = (moveEvent) => {
      const [x, y] = this.toModel(moveEvent);
      this.guardPoints[index] = [x, y];
      handle.setAttribute("x", x - 2.5);
      handle.setAttribute("y", -y - 2.5);
      this.guardPath.setAttribute("d", this.guardData());
      this.guardHit.setAttribute("d", this.pathData(closedCatmullRom(this.guardPoints, 8)));
    };
    const end = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", end);
      window.removeEventListener("pointercancel", end);
      handle.classList.remove("dragging");
      // Stored like the body's points, before the body's widening.
      this.commitGuard();
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
  },

  // Drag the whole guard by its edge. Dropped on "Create NC file" it stays
  // put and gets its own programs; dropped elsewhere its points move.
  startGuardMove(event) {
    if (event.button !== 0 || event.altKey) return;
    const start = this.toModel(event);
    const startX = event.clientX, startY = event.clientY;
    const members = [this.guardPath, this.guardHit, ...this.svg.querySelectorAll(".guard-handle")];
    const drop = document.getElementById("body-editor-nc");
    const overDrop = (pointer) => {
      const box = drop.getBoundingClientRect();
      return pointer.clientX >= box.left && pointer.clientX <= box.right
        && pointer.clientY >= box.top && pointer.clientY <= box.bottom;
    };
    let delta = [0, 0];
    this.guardMoved = false;
    const move = (moveEvent) => {
      // A few pixels of jitter is still a click.
      if (!this.guardMoved && Math.hypot(moveEvent.clientX - startX, moveEvent.clientY - startY) < 4) return;
      this.guardMoved = true;
      this.svg.classList.add("dragging");
      const [x, y] = this.toModel(moveEvent);
      delta = [x - start[0], y - start[1]];
      for (const member of members) member.setAttribute("transform", `translate(${delta[0]} ${-delta[1]})`);
      drop.classList.toggle("over", overDrop(moveEvent));
    };
    const end = (endEvent) => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", end);
      window.removeEventListener("pointercancel", end);
      drop.classList.remove("over");
      this.svg.classList.remove("dragging");
      if (!this.guardMoved) return;
      for (const member of members) member.removeAttribute("transform");
      if (endEvent && overDrop(endEvent)) {
        this.createNc("pickguard");
        return;
      }
      this.guardPoints = this.guardPoints.map(([x, y]) => [x + delta[0], y + delta[1]]);
      this.commitGuard();
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
  },

  // An open line as path data.
  openPath(points) {
    return points.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(2)},${(-y).toFixed(2)}`).join(" ");
  },

  // Drag one of a contour line's points; on drop its points are written
  // (drawn from now on: Auto arm contour / Auto belly cut goes back).
  startContourDrag(event, key, index, handle) {
    event.preventDefault();
    event.stopPropagation();
    const line = this.contourLines[key];
    handle.classList.add("dragging");
    const move = (moveEvent) => {
      const [x, y] = this.toModel(moveEvent);
      line.points[index] = [x, y];
      handle.setAttribute("cx", x);
      handle.setAttribute("cy", -y);
      const d = this.openPath(openCatmullRom(line.points, 8));
      line.path.setAttribute("d", d);
      line.hit.setAttribute("d", d);
    };
    const end = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", end);
      window.removeEventListener("pointercancel", end);
      handle.classList.remove("dragging");
      this.commitContour(key);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
  },

  // Write a line's points (stored before the body's widening) and lay
  // the body out again.
  commitContour(key) {
    const line = this.contourLines[key];
    const points = line.points.map((p) => this.unwiden(p).map((v) => Math.round(v * 10) / 10));
    this.setField(this.field("prototype.body_shape", line.spec.field), points);
    this.refresh();
  },

  addContourPoint(key, event) {
    const line = this.contourLines[key];
    const [x, y] = this.toModel(event);
    // After the point whose span passes nearest the click (8 samples a span).
    const samples = openCatmullRom(line.points, 8);
    let best = 0, bestDistance = Infinity;
    samples.forEach(([lx, ly], i) => {
      const distance = (lx - x) ** 2 + (ly - y) ** 2;
      if (distance < bestDistance) { bestDistance = distance; best = i; }
    });
    const span = Math.min(Math.floor(best / 8), line.points.length - 2);
    line.points.splice(span + 1, 0, [x, y]);
    this.commitContour(key);
  },

  removeContourPoint(key, index) {
    const line = this.contourLines[key];
    if (line.points.length <= 3) {
      this.setStatus(`The ${line.spec.label}'s line needs at least three points.`, "bad");
      return;
    }
    line.points.splice(index, 1);
    this.commitContour(key);
  },

  autoContour(key) {
    const spec = CONTOUR_LINES.find((s) => s.key === key);
    this.setField(this.field("prototype.body_shape", spec.field), []);
    this.refresh();
  },

  // The guard's outline as path data, its openings and holes as more
  // subpaths (cut out by the even-odd fill).
  guardData() {
    const guard = this.layout.pickguard;
    let d = this.pathData(closedCatmullRom(this.guardPoints, 8));
    for (const opening of guard.openings) d += " " + this.pathData(opening);
    for (const hole of guard.holes) {
      d += ` M${hole.x - hole.r},${-hole.y} a${hole.r},${hole.r} 0 1,0 ${2 * hole.r},0 a${hole.r},${hole.r} 0 1,0 ${-2 * hole.r},0`;
    }
    return d;
  },

  // A frame with its opening and holes cut out of it (even-odd).
  frameData(frameIndex) {
    const frame = this.layout.frames[frameIndex];
    let d = this.pathData(closedCatmullRom(this.frameHandles[frameIndex], 8));
    for (const opening of frame.openings) d += " " + this.pathData(opening);
    for (const hole of frame.holes) {
      d += ` M${hole.x - hole.r},${-hole.y} a${hole.r},${hole.r} 0 1,0 ${2 * hole.r},0 a${hole.r},${hole.r} 0 1,0 ${-2 * hole.r},0`;
    }
    return d;
  },

  // An editor point in a frame's own frame: along the neck and across
  // it (narrowed back by half its stretch past the middle).
  toFrame(frameIndex, [x, y]) {
    const frame = this.layout.frames[frameIndex];
    const dx = x - frame.origin[0], dy = y - frame.origin[1];
    const a = dx * frame.along[0] + dy * frame.along[1];
    const stretched = dx * frame.across[0] + dy * frame.across[1];
    const half = frame.stretch / 2;
    const c = stretched > half ? stretched - half : stretched < -half ? stretched + half : 0;
    return [Math.round(a * 10) / 10, Math.round(c * 10) / 10];
  },

  startFrameDrag(event, frameIndex, index, handle) {
    event.preventDefault();
    event.stopPropagation();
    handle.classList.add("dragging");
    const move = (moveEvent) => {
      const point = this.toModel(moveEvent);
      this.frameHandles[frameIndex][index] = point;
      handle.setAttribute("cx", point[0]);
      handle.setAttribute("cy", -point[1]);
      this.framePaths[frameIndex].setAttribute("d", this.frameData(frameIndex));
    };
    const end = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", end);
      window.removeEventListener("pointercancel", end);
      handle.classList.remove("dragging");
      this.commitFrame(frameIndex);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
  },

  // Write the frame's points (drawn from now on) and lay the body out again.
  commitFrame(frameIndex) {
    const frame = this.layout.frames[frameIndex];
    const points = this.frameHandles[frameIndex].map((p) => this.toFrame(frameIndex, p));
    this.setField(this.field("prototype", frame.field), points);
    this.refresh();
  },

  addFramePoint(event, frameIndex) {
    const [x, y] = this.toModel(event);
    const handles = this.frameHandles[frameIndex];
    // After the point whose span passes nearest the click (8 samples a span).
    const outline = closedCatmullRom(handles, 8);
    let best = 0, bestDistance = Infinity;
    outline.forEach(([ox, oy], i) => {
      const distance = (ox - x) ** 2 + (oy - y) ** 2;
      if (distance < bestDistance) { bestDistance = distance; best = i; }
    });
    handles.splice(Math.floor(best / 8) + 1, 0, [x, y]);
    this.commitFrame(frameIndex);
  },

  removeFramePoint(frameIndex, index) {
    if (this.frameHandles[frameIndex].length <= 4) {
      this.setStatus("A frame needs at least four points.", "bad");
      return;
    }
    this.frameHandles[frameIndex].splice(index, 1);
    this.commitFrame(frameIndex);
  },

  // Write the guard's points (drawn from now on) and lay the body out again.
  commitGuard() {
    const points = this.guardPoints.map((p) => this.unwiden(p).map((v) => Math.round(v * 10) / 10));
    this.setField(this.field("prototype.body_shape", "pickguard_points"), points);
    this.refresh();
  },

  addGuardPoint(event) {
    const [x, y] = this.toModel(event);
    // After the point whose span passes nearest the click (8 samples a span).
    const outline = closedCatmullRom(this.guardPoints, 8);
    let best = 0, bestDistance = Infinity;
    outline.forEach(([ox, oy], i) => {
      const distance = (ox - x) ** 2 + (oy - y) ** 2;
      if (distance < bestDistance) { bestDistance = distance; best = i; }
    });
    this.guardPoints.splice(Math.floor(best / 8) + 1, 0, [x, y]);
    this.commitGuard();
  },

  removeGuardPoint(index) {
    if (this.guardPoints.length <= 4) {
      this.setStatus("The pickguard needs at least four points.", "bad");
      return;
    }
    this.guardPoints.splice(index, 1);
    this.commitGuard();
  },

  autoGuard() {
    this.setField(this.field("prototype.body_shape", "pickguard_points"), []);
    this.refresh();
  },

  // Drag one point of a step's line; on drop every step's points are
  // written (drawn from now on: Auto steps goes back to the insets).
  startStepDrag(event, lineIndex, index, handle) {
    event.preventDefault();
    event.stopPropagation();
    // A handle left from before the last redraw no longer has its point.
    if (!this.stepPoints || index >= this.stepPoints[lineIndex].length) return;
    handle.classList.add("dragging");
    const move = (moveEvent) => {
      const [x, y] = this.toModel(moveEvent);
      this.stepPoints[lineIndex][index] = [x, y];
      handle.setAttribute("x", x - 2);
      handle.setAttribute("y", -y - 2);
      handle.setAttribute("transform", `rotate(45 ${x} ${-y})`);
      this.stepPaths[lineIndex].setAttribute("d", this.pathData(this.stepPoints[lineIndex]));
    };
    const end = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", end);
      window.removeEventListener("pointercancel", end);
      handle.classList.remove("dragging");
      this.commitSteps();
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
  },

  // Write every step's points (stored like the body's, before its
  // widening) and lay the body out again.
  commitSteps() {
    const lines = this.stepPoints.map((line) => line
      .filter((p) => Array.isArray(p))
      .map((p) => this.unwiden(p).map((v) => Math.round(v * 10) / 10)));
    this.setField(this.field("prototype.body_shape", "step_points"), lines);
    this.refresh();
  },

  // A click on a step's line adds a point on its nearest straight span.
  addStepPoint(event, lineIndex) {
    const [x, y] = this.toModel(event);
    const line = this.stepPoints[lineIndex];
    let best = 0, bestDistance = Infinity;
    line.forEach(([ax, ay], i) => {
      const [bx, by] = line[(i + 1) % line.length];
      const dx = bx - ax, dy = by - ay;
      const t = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy || 1)));
      const distance = (ax + t * dx - x) ** 2 + (ay + t * dy - y) ** 2;
      if (distance < bestDistance) { bestDistance = distance; best = i; }
    });
    line.splice(best + 1, 0, [x, y]);
    this.commitSteps();
  },

  removeStepPoint(lineIndex, index) {
    if (index >= this.stepPoints[lineIndex].length) return;
    if (this.stepPoints[lineIndex].length <= 3) {
      this.setStatus("A step's line needs at least three points.", "bad");
      return;
    }
    this.stepPoints[lineIndex].splice(index, 1);
    this.commitSteps();
  },

  autoSteps() {
    this.setField(this.field("prototype.body_shape", "step_points"), []);
    this.refresh();
  },

  // Make a feature's own NC programs (zeroed at its centre, its cover
  // plates included) and list them as downloads under the drop target.
  async createNc(group) {
    const list = document.getElementById("body-editor-nc-files");
    let payload;
    try {
      payload = collectValues();
    } catch (error) {
      this.setStatus(error.message, "bad");
      return;
    }
    this.setStatus("Making the NC files…", "");
    pyodide.globals.set("payload_json", JSON.stringify(payload));
    pyodide.globals.set("feature_group", group);
    const result = await runPython(
      "import json\nfrom cncguitarwizard.webapp import feature_programs\n" +
      "json.dumps(feature_programs(json.loads(payload_json), feature_group))"
    );
    if (result.error) {
      this.setStatus(result.error, "bad");
      return;
    }
    list.innerHTML = "";
    for (const file of result.files) {
      const item = document.createElement("li");
      const link = document.createElement("a");
      link.href = URL.createObjectURL(new Blob([file.text], { type: "text/plain" }));
      link.download = file.name;
      link.textContent = file.name;
      const button = document.createElement("button");
      button.className = "simulate";
      button.type = "button";
      button.textContent = "Simulate";
      button.title = "Copy this program to the clipboard and open NC Viewer below";
      button.addEventListener("click", () => simulate(file.name, file.text, list));
      item.append(link, " ", button);
      list.appendChild(item);
    }
    this.setStatus(`NC files for the ${result.title}, zeroed at its centre: download them below.`, "ok");
  },

  // Whether a group moved by [dx, dy] lies wholly outside the outline.
  leftBody(group, [dx, dy]) {
    const outline = this.outline();
    const points = [];
    for (const polygon of this.layout.polygons) {
      if (polygon.group === group) points.push(...polygon.points);
    }
    for (const circle of this.layout.circles) {
      if (circle.group !== group) continue;
      for (const [cx, cy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        points.push([circle.x + cx * circle.r, circle.y + cy * circle.r]);
      }
    }
    if (this.layout.jack && group === this.layout.jack.group) points.push([this.layout.jack.x, this.layout.jack.y]);
    return points.length > 0 && points.every(([x, y]) => !pointInPolygon(x + dx, y + dy, outline));
  },

  // What dropping a group off the body removes, or null when it cannot
  // go on its own (the switch cavity, the jack, a last pot or bolt).
  removal(group) {
    const shape = "prototype.body_shape";
    if (group.startsWith("pickup:")) {
      const position = group.split(":")[1];
      return {
        label: `the ${position} pickup`,
        apply: () => {
          const layoutField = this.field("prototype", "body_pickups");
          const names = ["neck", "middle", "bridge"];
          const types = layoutField.value === "custom"
            ? names.map((name) => this.field("prototype", `body_${name}_pickup`).value)
            : schema.pickup_configurations[layoutField.value];
          names.forEach((name, index) => {
            const value = name === position ? "none" : types[index];
            setControlValue(this.field("prototype", `body_${name}_pickup`), value);
          });
          setControlValue(layoutField, "custom");
        },
      };
    }
    if (group === "control") {
      return {
        label: "the controls (control cavity, pots and switch cavity)",
        apply: () => setControlValue(this.field("prototype", "body_controls"), "none"),
      };
    }
    if (group === "battery") {
      return {
        label: "the battery box",
        apply: () => setControlValue(this.field("prototype", "body_battery_box"), false),
      };
    }
    if (group.startsWith("pot:")) {
      const input = this.field(shape, "pot_offsets");
      const pots = readValue(input);
      const index = Number(group.split(":")[1]);
      if (pots.length < 2) return null;
      return {
        label: `pot ${index + 1}`,
        apply: () => this.setField(input, pots.filter((_, i) => i !== index)),
      };
    }
    if (group.startsWith("bolt:")) {
      const input = this.field(shape, "neck_bolts");
      let bolts = readValue(input);
      if (!bolts.length) {
        bolts = this.layout.circles
          .filter((c) => c.rear && c.name.startsWith("Neck bolt") && c.name.endsWith("ferrule"))
          .map((c) => [c.x, c.y]);
      }
      const index = Number(group.split(":")[1]);
      if (bolts.length < 2) return null;
      return {
        label: `neck bolt ${index + 1}`,
        apply: () => this.setField(input, bolts.filter((_, i) => i !== index)),
      };
    }
    return null;
  },

  setField(input, value) {
    if (!input) return;
    this.notice = "";
    input.value = input.dataset.type === "json" ? JSON.stringify(value) : String(value);
    markChanged(input);
    const fold = input.closest("details.advanced");
    if (fold) flagAdvancedSummary(fold);
    undoHistory.note();
  },

  shiftField(set, name, amount) {
    const input = this.field(set, name);
    if (input) this.setField(input, Math.round((readValue(input) + amount) * 10) / 10);
  },

  // The groups Shift-drag turns: the control cavity (with its cover, pots
  // or plate), the battery box, the jack and each pickup (about its own
  // centre). Round ones only move.
  turnable(group) {
    if (group && group.startsWith("pickup:")) return Boolean(this.layout.pickups && this.layout.pickups[group]);
    return group === "control" || group === "battery" || group === "jack";
  },

  // The point a group turns about, in the editor's frame (from the heel
  // end): the cavity's centre, a pickup's own centre, or the jack's socket.
  turnCentre(group) {
    if (group.startsWith("pickup:")) return this.layout.pickups[group].centre;
    if (group === "jack" && this.layout.jack) return [this.layout.jack.x, this.layout.jack.y];
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
      this.setStatus(`Turning ${this.groupLabel(group)} ${Math.round(degrees * 10) / 10}°`, "");
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

  // What the status line calls a group while it turns.
  groupLabel(group) {
    if (group === "control") return "the controls";
    if (group.startsWith("pickup:")) return `the ${group.split(":")[1]} pickup`;
    return `the ${group}`;
  },

  // Turn a group by `degrees` (counter-clockwise in the plan) about
  // `centre`: the fields that hold its angle, and a drawn almond's own
  // pots with it. A pickup's angle swings its treble end toward the tail,
  // so a counter-clockwise turn adds to it on the bass side's sign.
  applyTurn(group, degrees, [cx, cy]) {
    const shape = "prototype.body_shape";
    if (group.startsWith("pickup:")) {
      this.shiftField("prototype", this.layout.pickups[group].field, degrees * this.layout.bass_sign);
    } else if (group === "battery") {
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
          .filter((c) => c.rear && c.name.startsWith("Neck bolt") && c.name.endsWith("ferrule"))
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
    // Templates may share an outline (the Alexi Hexed's is the RR's):
    // the one chosen stays shown while the drawing is still it.
    const chosen = this.layout.templates[select.value];
    if (chosen && JSON.stringify(chosen.shape.control_points) === drawn) return;
    const match = Object.entries(this.layout.templates).find(
      ([, template]) => JSON.stringify(template.shape.control_points) === drawn
    );
    select.value = match ? match[0] : "";
    this.shown = select.value;
  },

  // Replace the drawing with a template, as soon as one is chosen in
  // Start from (Load loads it again): its outline and its switch, pot and
  // jack placements, which all stay editable afterwards — and any other
  // values it sets (the Alexi Hexed's pickup, controls, bridge and
  // pinstripe). What the template before it set besides its shape, and
  // is still as that left it, goes back to its default, so nothing of it
  // is left on the new one (an Alexi Hexed's stepped top on a Les Paul);
  // a value changed since is kept. Declined, Start from goes back.
  async reset() {
    if (!this.layout) return;
    const select = document.getElementById("body-editor-template");
    const key = select.value;
    const template = this.layout.templates[key];
    if (!template) return;
    const values = template.values || {};
    const leftovers = this.leftovers(template);
    const also = [
      Object.keys(values).length ? ` It also sets ${Object.keys(values).join(", ")}.` : "",
      Object.keys(leftovers).length ? ` ${Object.keys(leftovers).join(", ")} go back to their defaults.` : "",
    ].join("");
    if (!(await askConfirm(`Replace your drawing with ${template.label}?${also}`))) {
      select.value = this.shown || "";
      return;
    }
    const set = "prototype.body_shape";
    for (const [name, value] of Object.entries(template.shape)) {
      if (name === "kind" || name === "control_points") continue;
      this.setField(this.field(set, name), value);
    }
    if (Object.keys(values).length || Object.keys(leftovers).length) {
      applyValues("prototype", { ...leftovers, ...values });
      applyStringLimits();
    }
    this.loaded = key;
    this.shown = key;
    this.points = template.shape.control_points.map((p) => [...p]);
    this.commit();
    this.refresh();
  },

  // The values the template loaded before (or the one the drawing is)
  // set besides its shape, still as it left them, that the next one does
  // not set: each with its default, to put back.
  leftovers(template) {
    const previous = this.layout.templates[this.loaded || this.shown];
    if (!previous || previous === template) return {};
    let now;
    try {
      now = collectValues().prototype;
    } catch (error) {
      return {};
    }
    // Key order aside: a bridge's fields come back in the form's order.
    const canonical = (value) => JSON.stringify(value, (_, v) => (
      v && typeof v === "object" && !Array.isArray(v)
        ? Object.fromEntries(Object.entries(v).sort(([a], [b]) => a.localeCompare(b)))
        : v
    ));
    const defaults = {};
    for (const [name, value] of Object.entries(previous.values || {})) {
      if (name in (template.values || {})) continue;
      if (canonical(now[name]) !== canonical(value)) continue;
      const input = this.field("prototype", name);
      defaults[name] = variantFields[name]
        ? variantFields[name].default
        : input ? JSON.parse(input.dataset.default) : undefined;
      if (defaults[name] === undefined) delete defaults[name];
    }
    return defaults;
  },

  commit() {
    this.notice = "";
    this.input.value = JSON.stringify(this.points);
    markChanged(this.input);
    const fold = this.input.closest("details.advanced");
    if (fold) flagAdvancedSummary(fold);
    undoHistory.note();
  },

  // Report features left outside the outline and the body's size.
  check() {
    const outline = this.outline();
    const xs = outline.map((p) => p[0]), ys = outline.map((p) => p[1]);
    this.size.textContent = `— ${(Math.max(...xs) - Math.min(...xs)).toFixed(0)} × ${(Math.max(...ys) - Math.min(...ys)).toFixed(0)} mm`;
    const outside = new Set();
    for (const polygon of this.layout.polygons) {
      // Contours follow the outline itself, so they are laid out from it.
      if (polygon.role === "neck" || polygon.role === "plateau" || polygon.role.startsWith("contour")) continue;
      // The pocket opens onto the horn gap: only its tail wall must be in wood.
      const points = polygon.role === "pocket" ? polygon.points.filter((p) => p[0] > -1) : polygon.points;
      if (points.some(([x, y]) => !pointInPolygon(x, y, outline))) outside.add(polygon.name);
    }
    for (const circle of this.layout.circles) {
      if (!pointInPolygon(circle.x, circle.y, outline)) outside.add(circle.name);
    }
    const controls = this.field("prototype", "body_controls");
    const jackMisses = this.layout.jack && !this.layout.jack.reaches_controls && controls && controls.value !== "none";
    const jackNote = jackMisses
      ? " The jack's bore misses the control cavity: Shift-drag the jack to turn it toward it."
      : "";
    const frameProblem = (this.layout.frames || []).find((frame) => frame.problem);
    const cutBack = (this.layout.frames || []).filter((frame) => frame.adjusted && !frame.problem)
      .map((frame) => frame.position);
    const frameNote = cutBack.length === 1
      ? ` The ${cutBack[0]} pickup's frame was cut back to fit; drag its points to change it.`
      : cutBack.length
        ? ` The ${cutBack.join(" and ")} pickups' frames were cut back to fit; drag their points to change them.`
        : "";
    if (outside.size) {
      this.setStatus(`Outside the outline: ${[...outside].join(", ")}.${jackNote}`, "bad");
    } else if (frameProblem) {
      this.setStatus(`${frameProblem.problem} Drag its points in (or turn it round with body_pickup_frame_direction).`, "bad");
    } else if (jackMisses) {
      this.setStatus(jackNote.trim(), "bad");
    } else if (this.guardGaveWay()) {
      this.setStatus("Every feature fits inside the outline. The drawn pickguard does not cover the controls mounted in it, so the automatic one is used.", "ok");
    } else {
      this.setStatus(`Every feature fits inside the outline.${frameNote}`, "ok");
    }
  },

  // Whether a drawn pickguard gave way to the automatic one, which the
  // controls in the guard (body_controls "pickguard") need over them.
  guardGaveWay() {
    const guard = this.layout.pickguard;
    const drawn = this.field("prototype.body_shape", "pickguard_points");
    return Boolean(guard && guard.automatic && drawn && readValue(drawn).length);
  },

  setStatus(text, kind) {
    showEditorStatus(this, text, kind);
  },
};

document.getElementById("body-editor-reset").addEventListener("click", () => bodyEditor.reset());
document.getElementById("body-editor-turn").addEventListener("click", () => bodyEditor.turn(!bodyEditor.upright));

// Zoom an editor's drawing: Ctrl/Cmd + wheel, or a trackpad's pinch, about
// the pointer (up to 20 times); zoomed in, dragging its background moves
// it, and a double-click on the background, or the chip in its corner
// that says how far it is zoomed, fits the whole drawing again (the chip
// a touch screen's way back). The plain wheel scrolls the page as ever.
// The zoom (scale and centre in the drawing's view box) outlasts a redraw
// (see begin).
const ZOOM_TARGETS = ".handle, .frame-handle, .guard-handle, .step-handle, .contour-handle, " +
  ".stretch-handle, .movable, .outline-hit, .inlay-handle, .inlay-hit, .lettering-hit, " +
  ".cover-handle, .cover-stretch, .tuner-hole";

function enableZoom(editor) {
  const svg = editor.svg;
  const frame = document.createElement("div");
  frame.className = "zoom-frame";
  svg.before(frame);
  const chip = document.createElement("button");
  chip.type = "button";
  chip.className = "secondary zoom-chip";
  chip.title = "Fit the whole drawing again (or double-click it)";
  chip.hidden = true;
  frame.append(svg, chip);
  editor.showZoom = () => {
    chip.hidden = !editor.zoom;
    if (editor.zoom) chip.textContent = `${editor.zoom.scale.toFixed(1)}× · Fit`;
  };
  const fit = () => {
    editor.zoom = null;
    svg.setAttribute("viewBox", editor.baseBox.join(" "));
    editor.showZoom();
  };
  chip.addEventListener("click", fit);
  const setBox = (x, y, width, height) => {
    const [, , baseWidth] = editor.baseBox;
    const scale = baseWidth / width;
    editor.zoom = scale <= 1.0001 ? null : { scale, cx: x + width / 2, cy: y + height / 2 };
    svg.setAttribute("viewBox", (editor.zoom ? [x, y, width, height] : editor.baseBox).join(" "));
    editor.showZoom();
  };
  svg.addEventListener("wheel", (event) => {
    if (!(event.ctrlKey || event.metaKey) || !editor.baseBox) return;
    event.preventDefault();
    const [, , baseWidth, baseHeight] = editor.baseBox;
    const box = svg.viewBox.baseVal;
    const point = svg.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    const at = point.matrixTransform(svg.getScreenCTM().inverse());
    const scale = Math.min(20, Math.max(1, (baseWidth / box.width) * Math.exp(-event.deltaY * 0.002)));
    const width = baseWidth / scale, height = baseHeight / scale;
    // The point under the pointer stays where it is.
    setBox(at.x - (at.x - box.x) * width / box.width, at.y - (at.y - box.y) * height / box.height, width, height);
  }, { passive: false });
  svg.addEventListener("pointerdown", (event) => {
    if (!editor.zoom || event.button !== 0 || event.target.closest(ZOOM_TARGETS)) return;
    const start = [event.clientX, event.clientY];
    const box = svg.viewBox.baseVal;
    const from = [box.x, box.y, box.width, box.height];
    const ratio = svg.getScreenCTM().a;
    const move = (moveEvent) => {
      setBox(from[0] - (moveEvent.clientX - start[0]) / ratio, from[1] - (moveEvent.clientY - start[1]) / ratio,
        from[2], from[3]);
    };
    const end = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", end);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
  });
  svg.addEventListener("dblclick", (event) => {
    if (!editor.zoom || event.target.closest(ZOOM_TARGETS)) return;
    fit();
  });
}
// A plot (the plan view, a toolpath plot) zooms as an editor's drawing
// does: its own view box is the whole of it.
function zoomablePlot(holder) {
  const svg = holder.querySelector("svg");
  const baseBox = svg?.getAttribute("viewBox")?.trim().split(/[\s,]+/).map(Number);
  if (!baseBox || baseBox.length !== 4 || !(baseBox[2] > 0)) return;
  enableZoom({ svg, baseBox, zoom: null });
}

// A built result prints as a sheet for the workshop (the Print button, or
// the browser's own printing): the guitar's name, instrument and the day
// at its head, every program unfolded; the page's CSS leaves the rest out.
// Nothing built, the page prints as it is.
let programsOpenBeforePrint = false;

window.addEventListener("beforeprint", () => {
  const built = !output.classList.contains("hidden");
  document.body.classList.toggle("print-result", built);
  if (!built) return;
  const instrument = instrumentSelect.selectedOptions[0]?.textContent ?? "";
  const name = guitarName.value.trim() || "Prototype001";
  document.getElementById("print-title").textContent =
    `${name} — ${instrument} · ${new Date().toLocaleDateString()}`;
  const programs = document.getElementById("summary-programs");
  programsOpenBeforePrint = programs.open;
  programs.open = true;
});
window.addEventListener("afterprint", () => {
  if (!document.body.classList.contains("print-result")) return;
  document.body.classList.remove("print-result");
  document.getElementById("summary-programs").open = programsOpenBeforePrint;
});
document.getElementById("print-result").addEventListener("click", () => window.print());

// The quick links, each only while its panel shows (a result once one is
// built, the headstock editor while there is a headstock to draw, …).
const jumpLinks = [...document.querySelectorAll("#jump a[data-panel]")];
function syncJump() {
  for (const link of jumpLinks) {
    link.hidden = document.getElementById(link.dataset.panel).classList.contains("hidden");
  }
}
const panelWatch = new MutationObserver(syncJump);
for (const link of jumpLinks) {
  panelWatch.observe(document.getElementById(link.dataset.panel), { attributes: true, attributeFilter: ["class"] });
}
syncJump();

// The list of shortcuts: from the header, or ? anywhere but a field.
const keysDialog = document.getElementById("keys-dialog");
document.getElementById("show-keys").addEventListener("click", () => keysDialog.showModal());
document.addEventListener("keydown", (event) => {
  if (event.key !== "?" || event.ctrlKey || event.metaKey || event.altKey) return;
  if (event.target.closest?.("input, select, textarea, [contenteditable]")) return;
  if (document.querySelector("dialog[open]")) return;
  event.preventDefault();
  keysDialog.showModal();
});

// A menu (File ▾) closes once one of its buttons is chosen, on a click
// anywhere else, or on Escape (the keyboard back on its title).
for (const menu of document.querySelectorAll("details.menu")) {
  menu.addEventListener("click", (event) => {
    if (event.target.closest(".menu-items button")) menu.open = false;
  });
}
document.addEventListener("click", (event) => {
  for (const menu of document.querySelectorAll("details.menu[open]")) {
    if (!menu.contains(event.target)) menu.open = false;
  }
});
document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  for (const menu of document.querySelectorAll("details.menu[open]")) {
    if (menu.contains(document.activeElement)) menu.querySelector("summary").focus();
    menu.open = false;
    event.preventDefault();
  }
});

// The body editor's Auto buttons only where they do something (a
// pickguard, an arm contour, a stepped top, a belly cut on), and New
// pattern with an engraving laid out at random (not a drawn one).
function syncBodyButtons() {
  const field = (name) => form.querySelector(`[data-set="prototype"][data-name="${name}"]`);
  const on = (name) => Boolean(field(name)?.checked);
  const positive = (name) => Number(field(name)?.value) > 0;
  const shown = {
    "body-editor-auto-guard": on("body_pickguard"),
    "body-editor-auto-arm": positive("body_arm_contour_depth"),
    "body-editor-auto-steps": on("body_stepped_top"),
    "body-editor-auto-belly": positive("body_belly_cut_depth"),
    "body-editor-new-pattern": on("body_engraving") && field("body_engraving_pattern")?.value !== "drawn",
  };
  for (const [id, visible] of Object.entries(shown)) document.getElementById(id).hidden = !visible;
}
form.addEventListener("change", syncBodyButtons);
form.addEventListener("input", syncBodyButtons);
try {
  if (localStorage.getItem("cncguitarwizard.bodyUpright") === "1") bodyEditor.turn(true);
} catch {
  // No storage: sideways, as by default.
}
document.getElementById("body-editor-template").addEventListener("change", () => bodyEditor.reset());
document.getElementById("body-editor-auto-guard").addEventListener("click", () => bodyEditor.autoGuard());
document.getElementById("body-editor-auto-steps").addEventListener("click", () => bodyEditor.autoSteps());
document.getElementById("body-editor-auto-arm").addEventListener("click", () => bodyEditor.autoContour("arm"));
document.getElementById("body-editor-auto-belly").addEventListener("click", () => bodyEditor.autoContour("belly"));
// A new engraving pattern: another seed (turning the engraving on).
document.getElementById("body-editor-new-pattern").addEventListener("click", () => {
  setControlValue(bodyEditor.field("prototype", "body_engraving"), true);
  rerollSeed(bodyEditor.field("prototype", "body_engraving_seed"));
});
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

// A drawn headstock's edges meet in a point when their tip corners lie
// closer than this (Python's TIP_POINT_WIDTH); dragged within the snap
// distance, the corners are brought together.
const HEADSTOCK_TIP_POINT = 1.0;
const HEADSTOCK_POINT_SNAP = 3.0;

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
  template: null,  // the neck template last loaded on this form

  inputs() {
    return {
      bass: form.querySelector("[data-set='prototype'][data-name='headstock_bass_edge']"),
      treble: form.querySelector("[data-set='prototype'][data-name='headstock_treble_edge']"),
      tip: form.querySelector("[data-set='prototype'][data-name='headstock_tip_points']"),
      outline: form.querySelector("[data-set='prototype'][data-name='headstock_outline']"),
      holes: form.querySelector("[data-set='prototype'][data-name='tuner_hole_points']"),
    };
  },

  sync() {
    const { outline, bass, treble } = this.inputs();
    // A headless neck has no headstock to draw.
    const headless = form.querySelector("[data-set='prototype'][data-name='headless']");
    const active = outline && outline.value === "drawn" && !(headless && headless.checked);
    this.panel.classList.toggle("hidden", !active);
    showMirroredRows();
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
    return bodyEditor.element.call(this, name, attributes, parent);
  },

  begin(mirrored, minX, minY, maxX, maxY) {
    return bodyEditor.begin.call(this, mirrored, minX, minY, maxX, maxY);
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

  // Whether the edges meet in a point at the tip (closer than
  // TIP_POINT_WIDTH, as Python's HeadstockPlan.pointed).
  pointed() {
    const [low, high] = this.tipCorners();
    return high - low < HEADSTOCK_TIP_POINT;
  },

  // Where a pointed tip's edges meet.
  tipPoint() {
    const [low, high] = this.tipCorners();
    return [-this.length(), (low + high) / 2];
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
    if (this.pointed()) return [this.tipPoint(), this.tipPoint()];
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
    const bass = this.samples("bass"), treble = this.samples("treble");
    const tip = this.tipSamples();
    const all = [...bass, ...treble, ...tip, ...layout.holes.map((h) => [h.x, h.y])];
    const xs = all.map((p) => p[0]), ys = all.map((p) => p[1]);
    const margin = 25;
    const minX = Math.min(...xs) - margin, maxX = 70;
    const minY = Math.min(...ys) - margin, maxY = Math.max(...ys) + margin;
    this.begin(layout.mirrored, minX, minY, maxX, maxY);
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
    // The nut: the board running on past the nut line (a slotted or
    // zero-fret nut's, a locking nut's shelf), the nut on it, a zero fret.
    const nut = layout.nut;
    if (nut) {
      if (nut.board) this.element("path", { d: this.pathData(nut.board) + " Z", fill: "#3b2a1a", "fill-opacity": 0.85 });
      const look = nut.locking
        ? { fill: "#3c3c3c", stroke: "#111" }
        : { fill: "#efe8d6", stroke: "#8a7a5a" };
      const shape = this.element("path", { d: this.pathData(nut.nut) + " Z", "stroke-width": 0.4, ...look });
      this.element("title", {}, shape).textContent = "The nut (nut_style)";
      if (nut.zero_fret) {
        const [[x1, y1], [x2, y2]] = nut.zero_fret;
        const fret = this.element("line", { x1, y1: -y1, x2, y2: -y2, stroke: "#d9c9a8", "stroke-width": 1.2 });
        this.element("title", {}, fret).textContent = "The zero fret, on the nut line";
      }
    }
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
    // The tuner holes, each with the edge's clearance round it (dashed):
    // drag one to move it.
    this.holeNodes = layout.holes.map((hole, index) => {
      const ring = this.element("circle", { cx: hole.x, cy: -hole.y, r: layout.min_edge_distance, fill: "none", stroke: "#8a4b1e", "stroke-width": 0.25, "stroke-dasharray": "1.5,1.5", "pointer-events": "none" });
      const node = this.element("circle", { class: "tuner-hole", cx: hole.x, cy: -hole.y, r: hole.r });
      node.addEventListener("pointerdown", (event) => this.startHoleDrag(event, index, node));
      this.element("title", {}, node).textContent =
        `Tuner hole (${hole.side}) — drag to slide it along its edge, Shift-drag to move it anywhere`;
      return { node, ring };
    });
    // The truss-rod cover over the adjuster's trough (an adjuster at the
    // headstock), with its handles.
    if (layout.truss_cover) this.drawCover(layout.truss_cover);
    this.edgeHandles = { bass: [], treble: [] };
    for (const side of ["bass", "treble"]) {
      const sign = this.sign(side);
      this.edges[side].forEach(([d, h], index) => {
        const handle = this.element("circle", { class: "handle", cx: -d, cy: -sign * h, r: 2.2 });
        this.edgeHandles[side].push(handle);
        handle.addEventListener("pointerdown", (event) => this.startDrag(event, side, index, handle));
        handle.addEventListener("contextmenu", (event) => { event.preventDefault(); this.removePoint(side, index); });
      });
    }
    this.tip.forEach(([past, y], index) => {
      const handle = this.element("circle", { class: "handle", cx: -(this.length() + past), cy: -y, r: 2.2 });
      handle.addEventListener("pointerdown", (event) => this.startTipDrag(event, index, handle));
      handle.addEventListener("contextmenu", (event) => { event.preventDefault(); this.removeTipPoint(index); });
    });
    // The lettering, in blue as the body's engraving; drag it to move it.
    if (layout.lettering) {
      const group = this.element("g", { class: "lettering" });
      for (const line of layout.lettering.lines) {
        this.element("path", { class: "lettering-line", d: this.pathData(line) }, group);
        const hit = this.element("path", { class: "lettering-hit", d: this.pathData(line) }, group);
        hit.addEventListener("pointerdown", (event) => this.startLetteringDrag(event, group));
      }
      this.element("title", {}, group).textContent = "The headstock lettering — drag it to move it";
    }
    // Lines drawn on the face in another program (Import SVG), engraved
    // as the lettering is.
    if (layout.engraving) {
      const group = this.element("g", { class: "drawn-engraving" });
      for (const line of layout.engraving.lines) {
        this.element("path", { class: "lettering-line", d: this.pathData(line) }, group);
      }
      this.element("title", {}, group).textContent =
        "Engraved on the face, drawn in another program — Export SVG to change it";
    }
    this.check();
  },

  // The truss-rod cover: its trough dashed, the plate and its screws;
  // square handles on its corners (drag one to draw your own cover,
  // Alt/Option-click or right-click one to remove it, click its edge to
  // add one) and round ones past its far end and its widest side to make
  // it longer or wider.
  drawCover(cover) {
    const group = this.element("g", { class: "truss-cover" });
    this.element("path", { class: "cover-trough", d: this.pathData(cover.trough) + " Z" }, group);
    this.coverPath = this.element("path", { class: "cover-body", d: this.pathData(cover.outline) + " Z" }, group);
    const hit = this.element("path", { class: "outline-hit", d: this.pathData(cover.outline) + " Z", "stroke-width": 3 }, group);
    hit.addEventListener("click", (event) => {
      if (event.detail <= 1) this.addCoverCorner(event);
    });
    this.element("title", {}, hit).textContent = "The truss-rod cover — click its edge to add a corner";
    for (const [x, y] of cover.screws) {
      this.element("circle", { cx: x, cy: -y, r: cover.screw_radius, fill: "#fff", stroke: "#222", "stroke-width": 0.3, "pointer-events": "none" }, group);
    }
    cover.corners.forEach((corner, index) => {
      const [x, y] = this.coverPoint(corner);
      const handle = this.element("rect", { class: "cover-handle", x: x - 1.1, y: -y - 1.1, width: 2.2, height: 2.2 }, group);
      this.element("title", {}, handle).textContent = "A corner of the cover — drag it to draw your own cover, Alt/Option-click or right-click to remove it";
      handle.addEventListener("pointerdown", (event) => {
        if (event.altKey) {
          this.removeCoverCorner(index);
          return;
        }
        this.startCoverDrag(event, index, handle);
      });
      handle.addEventListener("contextmenu", (event) => {
        event.preventDefault();
        this.removeCoverCorner(index);
      });
    });
    const widest = cover.corners.reduce((best, c) => (Math.abs(c[1]) > Math.abs(best[1]) ? c : best));
    const [sideX, sideY] = this.coverPoint([widest[0], Math.abs(widest[1])]);
    const stretches = [
      ["length", [cover.back - cover.length - 3, 0], "Drag to make the cover longer or shorter (truss_rod_cover_length)"],
      ["width", [sideX, sideY + 3], "Drag to make the cover wider or narrower (truss_rod_cover_width)"],
    ];
    for (const [kind, [x, y], title] of stretches) {
      const handle = this.element("circle", { class: `cover-stretch ${kind}`, cx: x, cy: -y, r: 1.6 }, group);
      this.element("title", {}, handle).textContent = title;
      handle.addEventListener("pointerdown", (event) => this.startCoverStretch(event, kind, handle));
    }
  },

  // A cover corner or screw, (along, across) as truss_rod_cover_points
  // holds it, in the model frame.
  coverPoint([u, v]) {
    const cover = this.layout.truss_cover;
    return [cover.back - u * cover.length, (v * cover.width) / 2];
  },

  coverUnit([x, y]) {
    const cover = this.layout.truss_cover;
    return [Math.max(0, (cover.back - x) / cover.length), (2 * y) / cover.width];
  },

  // Drag a corner; the outline is shown straight between the corners
  // until Python rounds it again.
  startCoverDrag(event, index, handle) {
    event.preventDefault();
    event.stopPropagation();
    const corners = this.layout.truss_cover.corners.map((c) => [...c]);
    const start = this.toModel(event);
    const [x0, y0] = this.coverPoint(corners[index]);
    let moved = false;
    const preview = this.element("path", { class: "cover-preview" });
    const move = (moveEvent) => {
      const [x, y] = this.toModel(moveEvent);
      corners[index] = this.coverUnit([x0 + x - start[0], y0 + y - start[1]]);
      const [hx, hy] = this.coverPoint(corners[index]);
      handle.setAttribute("x", hx - 1.1);
      handle.setAttribute("y", -hy - 1.1);
      preview.setAttribute("d", this.pathData(corners.map((c) => this.coverPoint(c))) + " Z");
      moved = true;
    };
    const end = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", end);
      window.removeEventListener("pointercancel", end);
      if (moved) this.commitCover(corners);
      else preview.remove();
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
  },

  // A click on the cover's edge adds a corner on the nearest side.
  addCoverCorner(event) {
    const corners = this.layout.truss_cover.corners.map((c) => [...c]);
    const [x, y] = this.toModel(event);
    const points = corners.map((c) => this.coverPoint(c));
    let best = 0, bestDistance = Infinity;
    points.forEach(([ax, ay], i) => {
      const [bx, by] = points[(i + 1) % points.length];
      const dx = bx - ax, dy = by - ay;
      const t = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy || 1)));
      const distance = (ax + t * dx - x) ** 2 + (ay + t * dy - y) ** 2;
      if (distance < bestDistance) { bestDistance = distance; best = i; }
    });
    corners.splice(best + 1, 0, this.coverUnit([x, y]));
    this.commitCover(corners);
  },

  removeCoverCorner(index) {
    const corners = this.layout.truss_cover.corners.map((c) => [...c]);
    if (corners.length <= 3) return;
    corners.splice(index, 1);
    this.commitCover(corners);
  },

  // Write a drawn (custom) cover: its corners, the screws where they
  // were, and the size it was drawn at.
  commitCover(corners) {
    const cover = this.layout.truss_cover;
    const field = (name) => form.querySelector(`[data-set='prototype'][data-name='${name}']`);
    const unit = (point) => point.map((v) => Math.round(v * 10000) / 10000);
    setControlValue(field("truss_rod_cover_length"), cover.length);
    setControlValue(field("truss_rod_cover_width"), cover.width);
    setControlValue(field("truss_rod_cover_screws"), cover.screw_points.map(unit));
    setControlValue(field("truss_rod_cover_points"), corners.map(unit));
    const style = field("truss_rod_cover_style");
    if (style.value !== "custom") setControlValue(style, "custom");
    syncMirrors();
  },

  // Drag the round handle past the far end (length) or the widest side
  // (width); on drop the size is written, to the half millimetre.
  startCoverStretch(event, kind, handle) {
    event.preventDefault();
    event.stopPropagation();
    const cover = this.layout.truss_cover;
    const start = this.toModel(event);
    let size = cover[kind];
    const move = (moveEvent) => {
      const [x, y] = this.toModel(moveEvent);
      size = kind === "length"
        ? Math.max(5, cover.length + (start[0] - x))
        : Math.max(5, cover.width + 2 * (y - start[1]));
      if (kind === "length") handle.setAttribute("cx", x);
      else handle.setAttribute("cy", -y);
      this.setStatus(`Cover ${kind}: ${size.toFixed(1)} mm`, "ok");
    };
    const end = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", end);
      window.removeEventListener("pointercancel", end);
      if (size === cover[kind]) return;
      setControlValue(
        form.querySelector(`[data-set='prototype'][data-name='truss_rod_cover_${kind}']`),
        Math.round(size * 2) / 2,
      );
      syncMirrors();
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
  },

  // Drag the lettering; on drop its centre is written (headstock_engraving_x / _y).
  startLetteringDrag(event, group) {
    event.preventDefault();
    event.stopPropagation();
    const start = this.toModel(event);
    let delta = [0, 0];
    const move = (moveEvent) => {
      const [x, y] = this.toModel(moveEvent);
      delta = [x - start[0], y - start[1]];
      group.setAttribute("transform", `translate(${delta[0]} ${-delta[1]})`);
    };
    const end = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", end);
      window.removeEventListener("pointercancel", end);
      if (!delta[0] && !delta[1]) return;
      const [cx, cy] = this.layout.lettering.centre;
      const round = (v) => Math.round(v * 10) / 10;
      setControlValue(form.querySelector("[data-set='prototype'][data-name='headstock_engraving_x']"), round(cx + delta[0]));
      setControlValue(form.querySelector("[data-set='prototype'][data-name='headstock_engraving_y']"), round(cy + delta[1]));
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
  },

  toModel(event) {
    return bodyEditor.toModel.call(this, event);
  },

  // Move one handle; a tip handle sets the length of both edges. Tip
  // corners brought within HEADSTOCK_POINT_SNAP of each other meet in a
  // point; a pointed tip's corners then move together (the point), unless
  // Shift parts them.
  place(side, index, [x, y], part = false) {
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
      const other = side === "bass" ? "treble" : "bass";
      const otherEnd = this.edges[other][this.edges[other].length - 1];
      const otherY = this.sign(other) * otherEnd[1];
      if (this.dragPointed && !part) {
        // The point moves: both corners to it.
        edge[index][1] = half;
        otherEnd[1] = Math.round(y * this.sign(other) * 10) / 10;
        this.tip = [];
        return;
      }
      if (!part && Math.abs(y - otherY) < HEADSTOCK_POINT_SNAP) {
        // Close enough: they meet.
        edge[index][1] = Math.round(otherY * this.sign(side) * 10) / 10;
        this.tip = [];
        return;
      }
    } else {
      const low = index > 0 ? edge[index - 1][0] + 1 : 1;
      distance = Math.min(Math.max(distance, low), edge[index + 1][0] - 1);
      edge[index][0] = distance;
    }
    edge[index][1] = half;
  },

  // The edges and the tip drawn as they are now, not yet committed: a
  // drag under way, or the tour showing one.
  showEdges() {
    const bass = this.samples("bass"), treble = this.samples("treble");
    this.paths.bass.setAttribute("d", this.pathData(bass));
    this.paths.treble.setAttribute("d", this.pathData(treble));
    this.hits.bass.setAttribute("d", this.pathData(bass));
    this.hits.treble.setAttribute("d", this.pathData(treble));
    const tip = this.tipSamples();
    this.tipLine.setAttribute("d", this.pathData(tip));
    this.tipHit.setAttribute("d", this.pathData(tip));
  },

  startDrag(event, side, index, handle) {
    if (event.altKey) {
      this.removePoint(side, index);
      return;
    }
    event.preventDefault();
    handle.classList.add("dragging");
    // A pointed tip's corner drags the point, unless Shift parts them.
    this.dragPointed = index === this.edges[side].length - 1 && this.pointed();
    const insets = this.holeInsets();
    const move = (moveEvent) => {
      this.place(side, index, this.toModel(moveEvent), moveEvent.shiftKey);
      this.showEdges();
      this.followEdges(insets);
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
      if (this.holesMoved(insets)) this.commitHoles();
      this.draw();
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
  },

  // How far in from its own edge each tuner hole sits, at its distance
  // from the nut: a dragged edge keeps its holes that far in (see
  // followEdges).
  holeInsets() {
    return this.layout.holes.map((hole) => {
      const distance = -hole.x;
      return { distance, y: hole.y, inset: this.curve(hole.side)(distance) - hole.y / this.sign(hole.side) };
    });
  },

  // The holes moved with the edges as they are now, each its inset in
  // from its own edge; drawn, not yet committed.
  followEdges(insets) {
    this.layout.holes.forEach((hole, index) => {
      const { distance, inset } = insets[index];
      hole.y = this.sign(hole.side) * (this.curve(hole.side)(distance) - inset);
      this.showHole(index);
    });
  },

  // Whether a hole has left the place it had when the insets were taken.
  holesMoved(insets) {
    return this.layout.holes.some((hole, index) => Math.abs(hole.y - insets[index].y) > 0.05);
  },

  showHole(index) {
    const hole = this.layout.holes[index];
    for (const node of Object.values(this.holeNodes[index])) {
      node.setAttribute("cx", hole.x);
      node.setAttribute("cy", -hole.y);
    }
  },

  // Drag a tuner hole along its edge, kept as far in from it as it was,
  // so the tuner's key stays out past the edge; Shift-drag puts it
  // anywhere across. Along the neck it stays between its side's
  // neighbours (each side's holes run from the nut to the tip).
  startHoleDrag(event, index, node) {
    event.preventDefault();
    node.classList.add("dragging");
    const hole = this.layout.holes[index];
    const same = this.layout.holes.filter((other) => other.side === hole.side);
    const at = same.indexOf(hole);
    const nearer = at > 0 ? -same[at - 1].x + 1 : 1;
    const further = at < same.length - 1 ? -same[at + 1].x - 1 : Infinity;
    const sign = this.sign(hole.side);
    const edge = this.curve(hole.side);
    const inset = edge(-hole.x) - hole.y / sign;
    const move = (moveEvent) => {
      const [x, y] = this.toModel(moveEvent);
      const distance = Math.min(Math.max(-x, nearer), further);
      hole.x = -distance;
      hole.y = moveEvent.shiftKey ? y : sign * (edge(distance) - inset);
      this.showHole(index);
      this.check();
    };
    const end = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", end);
      window.removeEventListener("pointercancel", end);
      node.classList.remove("dragging");
      this.commitHoles();
      this.draw();
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
  },

  // Every hole's place as tuner_hole_points takes it: (distance from the
  // nut, offset toward its own side), in the layout's order.
  commitHoles() {
    const round = (value) => Math.round(value * 10) / 10;
    bodyEditor.setField(this.inputs().holes, this.layout.holes.map(
      (hole) => [round(-hole.x), round(hole.y / this.sign(hole.side))]
    ));
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
    if (this.pointed()) {
      this.setStatus("A pointed tip takes no tip handles: Shift-drag a tip corner to part the corners first.", "bad");
      return;
    }
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

  fillTemplates() {
    const select = document.getElementById("headstock-editor-template");
    // A new form (a reset, another instrument, a loaded design) has no
    // template on it.
    select.value = "";
    this.template = null;
    if (select.options.length || !schema.neck_templates) return;
    const none = document.createElement("option");
    none.value = "";
    none.textContent = "Choose a neck…";
    select.appendChild(none);
    for (const [key, template] of Object.entries(schema.neck_templates)) {
      const option = document.createElement("option");
      option.value = key;
      option.textContent = template.label;
      select.appendChild(option);
    }
  },

  // Load a neck template, as soon as one is chosen in Start from (Load
  // loads it again): its nut, headstock and truss rod values replace the
  // form's, the tuner and tip settings it does not set go back to their
  // defaults (resets), and the drawing becomes its outline (still
  // editable). Declined, Start from goes back to what it showed.
  async loadTemplate() {
    const select = document.getElementById("headstock-editor-template");
    const key = select.value;
    const template = schema.neck_templates && schema.neck_templates[key];
    if (!template) return;
    if (!(await askConfirm(
      `Load the ${template.label}? Its nut, headstock and truss rod settings replace yours.`
    ))) {
      select.value = this.template || "";
      return;
    }
    for (const [name, value] of Object.entries(template.values)) {
      const input = bodyEditor.field("prototype", name);
      if (input) setControlValue(input, value);
    }
    for (const name of template.resets || []) {
      const input = bodyEditor.field("prototype", name);
      if (input) setControlValue(input, JSON.parse(input.dataset.default));
    }
    this.template = key;
    select.value = key;
    this.sync();
  },

  // Back to the fitted outline: the edge fields are emptied, so the
  // drawing follows the fitted outline again until the next edit. It
  // works with no drawing too (one that could not be laid out), and lays
  // the headstock out afresh.
  async reset() {
    if (!(await askConfirm("Replace the drawn headstock with the fitted outline?"))) return;
    const { bass, treble, tip, holes } = this.inputs();
    bodyEditor.setField(bass, []);
    bodyEditor.setField(treble, []);
    bodyEditor.setField(tip, []);
    bodyEditor.setField(holes, []);
    this.tip = [];
    if (this.layout) {
      this.edges = structuredClone(this.layout.start_edges);
      this.draw();
    }
    this.refresh();
  },

  commit() {
    this.notice = "";
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
    // Two holes closer than their diameter and hole_clearance (as Python's
    // TunerLayout checks it).
    const holes = this.layout.holes;
    const crowded = holes.some((hole, i) => holes.slice(i + 1).some((other) =>
      Math.hypot(hole.x - other.x, hole.y - other.y) < hole.r + other.r + this.layout.hole_clearance - 0.05));
    this.size.textContent = `— ${this.reach().toFixed(0)} mm long`;
    const [low, high] = this.tipCorners();
    // Nowhere narrower than HEADSTOCK_TIP_POINT but a pointed tip's last
    // run, narrowing all the way to the point (as Python checks).
    const length = this.length(), pointed = this.pointed();
    const widths = [];
    for (let d = 0; d < length; d += 2.5) widths.push([d, bassCurve(d) + trebleCurve(d)]);
    const pinch = widths.find(([, width], i) => width < HEADSTOCK_TIP_POINT
      && !(pointed && width > 0 && widths.slice(i + 1).every(([, later]) => later <= width + 1e-9)));
    if (pinch) {
      this.setStatus(`The edges meet or cross ${pinch[0].toFixed(0)} mm from the nut: keep them apart, or bring both tip corners together for a pointed tip.`, "bad");
    } else if (this.tip.some(([, y]) => y <= low || y >= high)) {
      this.setStatus("A tip handle lies outside the tip's corners: move it in or remove it.", "bad");
    } else if (close.length) {
      this.setStatus(`Too close to the edge (keep ${limit} mm): ${close.join(", ")}.`, "bad");
    } else if (crowded) {
      this.setStatus(`Two tuner holes are too close: keep ${this.layout.hole_clearance} mm of wood between them.`, "bad");
    } else if (this.layout.truss_cover?.problem) {
      const problem = this.layout.truss_cover.problem;
      this.setStatus(`${problem[0].toUpperCase()}${problem.slice(1)}.`, "bad");
    } else if (this.layout.lettering?.problem) {
      this.setStatus(this.layout.lettering.problem, "bad");
    } else if (this.layout.engraving?.problem) {
      this.setStatus(this.layout.engraving.problem, "bad");
    } else {
      this.setStatus(`Every tuner hole is at least ${limit} mm from the edge.`, "ok");
    }
  },

  setStatus(text, kind) {
    showEditorStatus(this, text, kind);
  },
};

// The fret markers: the first marker's fret space, its shape edited as
// [along, across] points (inlay_points: along 0 at the fret toward the
// nut and 1 at the marker's fret, across the share of the board's
// half-width toward the bass edge), every other marker the same shape
// fitted to its own fret space (shown below it on the whole board).
const inlayEditor = {
  panel: document.getElementById("inlay-editor"),
  svg: document.getElementById("inlay-editor-svg"),
  boardSvg: document.getElementById("inlay-editor-board"),
  status: document.getElementById("inlay-editor-status"),
  size: document.getElementById("inlay-editor-size"),
  layout: null,
  points: [],
  refreshTimer: null,
  request: 0,

  async refresh() {
    if (!pyodide) return;
    let payload;
    try {
      payload = collectValues();
    } catch (error) {
      this.setStatus(`Cannot lay the markers out: ${error.message}`, "bad");
      return;
    }
    // Only the latest request is drawn: one overtaken by a newer form (a
    // design loaded meanwhile) is dropped.
    const request = ++this.request;
    let layout;
    try {
      pyodide.globals.set("payload_json", JSON.stringify(payload));
      layout = await runPython(
        "import json\nfrom cncguitarwizard.webapp import inlay_editor_layout\n" +
        "json.dumps(inlay_editor_layout(json.loads(payload_json)))"
      );
    } catch (error) {
      if (request === this.request) this.setStatus(`Cannot lay the markers out: ${error.message}`, "bad");
      return;
    }
    if (request !== this.request) return;
    if (layout.error) {
      this.setStatus(layout.error, "bad");
      return;
    }
    // A drawing that fails says why, rather than leaving the panes blank.
    try {
      this.layout = layout;
      this.points = layout.points.map((p) => [...p]);
      this.draw();
    } catch (error) {
      this.setStatus(`Cannot draw the markers: ${error.message}`, "bad");
    }
  },

  scheduleRefresh() {
    clearTimeout(this.refreshTimer);
    this.refreshTimer = setTimeout(() => this.refresh(), 400);
  },

  setStatus(text, kind) {
    showEditorStatus(this, text, kind);
  },

  element(name, attributes, parent) {
    return bodyEditor.element.call(this, name, attributes, parent);
  },

  begin(mirrored, minX, minY, maxX, maxY) {
    return bodyEditor.begin.call(this, mirrored, minX, minY, maxX, maxY);
  },

  pathData(points) {
    return bodyEditor.pathData(points);
  },

  toModel(event) {
    return bodyEditor.toModel.call(this, event);
  },

  // The board's half-width at a distance from the nut (its straight taper).
  half(x) {
    const layout = this.layout;
    return layout.nut_half + (layout.final_half - layout.nut_half) * x / layout.final_position;
  },

  // An [along, across] point in mm on the board (as built right-handed:
  // the bass edge at -Y), and back.
  toBoard([along, across]) {
    const { front, back, bass_sign: bass } = this.layout;
    const x = front + along * (back - front);
    return [x, bass * across * this.half(x)];
  },

  fromBoard([x, y]) {
    const { front, back, bass_sign: bass } = this.layout;
    return [(x - front) / (back - front), bass * y / this.half(x)];
  },

  draw() {
    const layout = this.layout;
    const { front, back } = layout;
    const pad = 6;
    const top = this.half(back) + 3;
    this.begin(layout.mirrored, front - pad, -top, back + pad, top);
    const grid = this.element("g", { stroke: "#eee6d8", "stroke-width": 0.15 });
    for (let x = Math.ceil((front - pad) / 5) * 5; x <= back + pad; x += 5) {
      this.element("line", { x1: x, y1: -top, x2: x, y2: top }, grid);
    }
    for (let y = -Math.floor(top / 5) * 5; y <= top; y += 5) {
      this.element("line", { x1: front - pad, y1: -y, x2: back + pad, y2: -y }, grid);
    }
    // The board between its edges, the two frets and the centreline.
    const x0 = front - pad, x1 = back + pad;
    this.element("path", {
      d: this.pathData([[x0, -this.half(x0)], [x1, -this.half(x1)], [x1, this.half(x1)], [x0, this.half(x0)]]),
      fill: "#5b3a24", "fill-opacity": 0.85, stroke: "none",
    });
    for (const x of [front, back]) {
      this.element("line", { x1: x, y1: -this.half(x), x2: x, y2: this.half(x), stroke: "#c9c9c9", "stroke-width": 0.6 });
    }
    this.element("line", { x1: x0, y1: 0, x2: x1, y2: 0, stroke: "#8a7a6a", "stroke-width": 0.15, "stroke-dasharray": "1,1" });
    // Inside the dashed line a corner keeps 1 mm from the frets and edges
    // in every marker's space (the shortest and the narrowest).
    const { along: [lo, hi], across } = layout.limits;
    this.element("path", {
      d: this.pathData([[lo, -across], [hi, -across], [hi, across], [lo, across]].map((p) => this.toBoard(p))),
      fill: "none", stroke: "#e8c27a", "stroke-width": 0.2, "stroke-dasharray": "0.8,0.6",
    });
    const shape = this.points.map((p) => this.toBoard(p));
    this.shapePath = this.element("path", {
      d: this.pathData(shape), fill: "#f4efe2", stroke: "#1f6fb2", "stroke-width": 0.3, "stroke-linejoin": "round",
    });
    const hit = this.element("path", { class: "inlay-hit", d: this.pathData(shape) });
    hit.addEventListener("click", (event) => this.addPoint(event));
    this.element("title", {}, hit).textContent = "Click a side to add a corner";
    this.handles = shape.map(([x, y], index) => {
      const handle = this.element("circle", { class: "inlay-handle", cx: x, cy: -y, r: shape.length > 12 ? 0.55 : 0.9 });
      this.element("title", {}, handle).textContent = "Marker corner — drag to shape it, Alt-click or right-click to remove it";
      handle.addEventListener("pointerdown", (event) => {
        if (event.altKey) { this.removePoint(index); return; }
        this.startDrag(event, index, handle);
      });
      handle.addEventListener("contextmenu", (event) => { event.preventDefault(); this.removePoint(index); });
      return handle;
    });
    this.drawBoard();
    this.size.textContent = `— fret ${layout.fret}, ${(back - front).toFixed(1)} mm between frets`;
    if (layout.problem) this.setStatus(layout.problem, "bad");
    else this.setStatus(layout.custom ? "Every marker is this shape, fitted to its fret." : "This style's marker: drag a corner to draw your own.", "ok");
  },

  // The whole board, nut to last fret, with every marker as it is cut.
  drawBoard() {
    const layout = this.layout;
    const svg = this.boardSvg;
    svg.innerHTML = "";
    const end = layout.final_position, top = layout.final_half + 2;
    const flip = layout.mirrored ? " scale(1,-1)" : "";
    svg.setAttribute("viewBox", `-4 ${-top} ${end + 8} ${2 * top}`);
    const root = document.createElementNS(SVG_NS, "g");
    root.setAttribute("transform", flip.trim());
    svg.appendChild(root);
    const add = (name, attributes) => {
      const node = document.createElementNS(SVG_NS, name);
      for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
      root.appendChild(node);
    };
    add("path", { d: this.pathData([[0, -layout.nut_half], [end, -layout.final_half], [end, layout.final_half], [0, layout.nut_half]]), fill: "#5b3a24", stroke: "none" });
    for (const [[ax, ay], [bx, by]] of layout.frets) {
      add("line", { x1: ax, y1: -ay, x2: bx, y2: -by, stroke: "#c9c9c9", "stroke-width": 0.5 });
    }
    for (const marker of layout.markers) {
      add("path", { d: this.pathData(marker), fill: "#f4efe2", stroke: "none" });
    }
  },

  startDrag(event, index, handle) {
    event.preventDefault();
    event.stopPropagation();
    if (index >= this.points.length) return;
    handle.classList.add("dragging");
    const move = (moveEvent) => {
      this.points[index] = this.kept(this.fromBoard(this.toModel(moveEvent)));
      const [x, y] = this.toBoard(this.points[index]);
      handle.setAttribute("cx", x);
      handle.setAttribute("cy", -y);
      this.shapePath.setAttribute("d", this.pathData(this.points.map((p) => this.toBoard(p))));
    };
    const end = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", end);
      window.removeEventListener("pointercancel", end);
      handle.classList.remove("dragging");
      this.commit();
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
  },

  // A corner held inside the limits, where it fits every marker.
  kept([along, across]) {
    const { along: [lo, hi], across: limit } = this.layout.limits;
    return [Math.min(hi, Math.max(lo, along)), Math.min(limit, Math.max(-limit, across))];
  },

  // A click on a side adds a corner on the nearest side.
  addPoint(event) {
    const [x, y] = this.kept(this.fromBoard(this.toModel(event)));
    const points = this.points;
    let best = 0, bestDistance = Infinity;
    points.forEach(([ax, ay], i) => {
      const [bx, by] = points[(i + 1) % points.length];
      const dx = bx - ax, dy = by - ay;
      const t = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy || 1)));
      const distance = (ax + t * dx - x) ** 2 + (ay + t * dy - y) ** 2;
      if (distance < bestDistance) { bestDistance = distance; best = i; }
    });
    points.splice(best + 1, 0, [x, y]);
    this.commit();
  },

  removePoint(index) {
    if (index >= this.points.length) return;
    if (this.points.length <= 3) {
      this.setStatus("A marker needs at least three corners.", "bad");
      return;
    }
    this.points.splice(index, 1);
    this.commit();
  },

  // Write the drawn shape (a drawn style from now on) and lay it out again.
  commit() {
    this.notice = "";
    const points = this.points.map(([along, across]) => [
      Math.round(along * 10000) / 10000, Math.round(across * 10000) / 10000,
    ]);
    setControlValue(form.querySelector('[data-set="prototype"][data-name="inlay_points"]'), points);
    const style = form.querySelector('[data-set="prototype"][data-name="inlay_style"]');
    if (style && style.value !== "custom") setControlValue(style, "custom");
    syncMirrors();
    this.refresh();
  },

  // Back to the block a drawn marker starts as.
  reset() {
    this.notice = "";
    setControlValue(form.querySelector('[data-set="prototype"][data-name="inlay_points"]'), []);
    this.refresh();
  },

  // Start from: every marker style but a drawn one, by its form label.
  fillTemplates() {
    const select = document.getElementById("inlay-editor-template");
    select.value = "";
    this.template = null;
    const field = schema && schema.prototype.flatMap((group) => group.fields)
      .find((candidate) => candidate.name === "inlay_style");
    if (select.options.length || !field) return;
    const none = document.createElement("option");
    none.value = "";
    none.textContent = "Choose a marker…";
    select.appendChild(none);
    for (const style of field.options.filter((option) => option !== "custom")) {
      const option = document.createElement("option");
      option.value = style;
      option.textContent = field.labels?.[style] ?? style;
      select.appendChild(option);
    }
  },

  // Load a style's marker, as soon as one is chosen in Start from (Load
  // loads it again): the style is set and a drawn marker let go of, so the
  // editor shows the style's own, to draw on from there. Declined (over a
  // drawn marker), Start from goes back to what it showed.
  async loadTemplate() {
    const select = document.getElementById("inlay-editor-template");
    const style = select.value;
    if (!style) return;
    const styleInput = form.querySelector('[data-set="prototype"][data-name="inlay_style"]');
    const pointsInput = form.querySelector('[data-set="prototype"][data-name="inlay_points"]');
    const label = select.selectedOptions[0].textContent;
    if (styleInput.value === "custom" && !(await askConfirm(
      `Start from the ${label} marker? It replaces the marker you drew.`
    ))) {
      select.value = this.template || "";
      return;
    }
    this.notice = "";
    setControlValue(pointsInput, []);
    setControlValue(styleInput, style);
    this.template = style;
    select.value = style;
    syncMirrors();
    this.refresh();
  },
};

document.getElementById("inlay-editor-reset").addEventListener("click", () => inlayEditor.reset());
for (const editor of [bodyEditor, headstockEditor, inlayEditor]) enableZoom(editor);
document.getElementById("inlay-editor-load").addEventListener("click", () => inlayEditor.loadTemplate());
document.getElementById("inlay-editor-template").addEventListener("change", () => inlayEditor.loadTemplate());
form.addEventListener("change", (event) => {
  if (event.target.dataset.name !== "inlay_points") inlayEditor.scheduleRefresh();
});

document.getElementById("headstock-editor-reset").addEventListener("click", () => headstockEditor.reset());
document.getElementById("headstock-editor-load").addEventListener("click", () => headstockEditor.loadTemplate());
document.getElementById("headstock-editor-template").addEventListener("change", () => headstockEditor.loadTemplate());
// A frame style chosen draws every frame as that style's own again.
form.addEventListener("change", (event) => {
  if (event.target.dataset.name !== "body_pickup_frame") return;
  for (const position of ["neck", "middle", "bridge"]) {
    const input = bodyEditor.field("prototype", `body_${position}_frame_points`);
    if (input && input.value !== "[]") bodyEditor.setField(input, []);
  }
  bodyEditor.scheduleRefresh();
});

// A cover style chosen goes back to that style's own size (a drawn cover
// keeps the size it was drawn at).
form.addEventListener("change", (event) => {
  if (event.target.dataset.name !== "truss_rod_cover_style" || event.target.value === "custom") return;
  for (const name of ["truss_rod_cover_length", "truss_rod_cover_width"]) {
    const input = form.querySelector(`[data-set='prototype'][data-name='${name}']`);
    if (input && input.value !== "") setControlValue(input, null);
  }
  syncMirrors();
});
form.addEventListener("change", (event) => {
  if (["headstock_outline", "headless"].includes(event.target.dataset.name)) headstockEditor.sync();
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
  // Controls mounted in the pickguard bring it with them.
  if (event.target.dataset.name === "body_controls" && event.target.value === "pickguard") {
    const guard = form.querySelector('[data-set="prototype"][data-name="body_pickguard"]');
    if (guard && !guard.checked) {
      guard.checked = true;
      markChanged(guard);
      syncMirrors();
    }
  }
  if (event.target.dataset.name !== "control_points") bodyEditor.scheduleRefresh();
});

instrumentSelect.addEventListener("change", async () => {
  if (form.querySelector(".changed") && !(await askConfirm(
    "Switch instrument? Every value goes back to that instrument's defaults."
  ))) {
    instrumentSelect.value = instrumentSelect.dataset.current;
    return;
  }
  instrumentSelect.dataset.current = instrumentSelect.value;
  renderForm();
  clearError();
});

buildButton.addEventListener("click", build);
document.getElementById("rebuild").addEventListener("click", build);
resetButton.addEventListener("click", reset);
saveDesignButton.addEventListener("click", saveDesign);
ncZipButton.addEventListener("click", downloadNcZip);
// The file chooser opens straight from the click: a browser lets a page
// open it only while handling the click itself (Safari not after a
// dialog has been answered), so the question comes once a file is chosen.
loadDesignButton.addEventListener("click", () => loadDesignFile.click());
for (const part of ["body", "headstock", "inlay"]) {
  for (const kind of ["svg", "dxf"]) {
    const suffix = kind === "svg" ? "" : "-dxf";
    document.getElementById(`${part}-editor-export${suffix}`).addEventListener("click", () => exportOutline(part, kind));
    document.getElementById(`${part}-editor-import${suffix}`).addEventListener("click", () => {
      // Either kind is read (told apart by its text); the chooser offers
      // the one asked for.
      outlineFile.accept = kind === "dxf" ? ".dxf" : ".svg,image/svg+xml";
      outlineFile.dataset.part = part;
      outlineFile.click();
    });
  }
}
outlineFile.addEventListener("change", () => {
  const [file] = outlineFile.files;
  outlineFile.value = "";
  if (file) importOutline(outlineFile.dataset.part, file);
});
// A design file to load (chosen, or dropped on the page): asked first
// when settings are changed.
async function openDesign(file) {
  if (form.querySelector(".changed") && !(await askConfirm(
    `Load ${file.name}? Every current value is replaced by the file's.`
  ))) return;
  loadDesign(file);
}
loadDesignFile.addEventListener("change", () => {
  const [file] = loadDesignFile.files;
  loadDesignFile.value = "";
  if (file) openDesign(file);
});

// The tuner holes go back to where the style lays them out when the style
// or its tuner settings are changed by hand (in the form or an editor's
// Settings), as they may then number or sit otherwise; a loaded design,
// an undo or a neck template keeps what it sets.
const TUNER_LAYOUT_FIELDS = new Set([
  "headstock_style", "string_count", "tuner_station_distances", "tuner_side_offsets",
  "tuner_inline_first_distance", "tuner_inline_spacing", "tuner_inline_offsets",
]);
document.addEventListener("change", (event) => {
  if (!event.isTrusted) return;
  const original = [...mirrors].find(([, copy]) => copy === event.target)?.[0] || event.target;
  if (original.dataset?.set !== "prototype" || !TUNER_LAYOUT_FIELDS.has(original.dataset.name)) return;
  const { holes } = headstockEditor.inputs();
  if (!holes || (!valueProblem(holes) && readValue(holes).length === 0)) return;
  bodyEditor.setField(holes, []);
  headstockEditor.scheduleRefresh();
});

// A file dragged onto the page: a design (.json) dropped anywhere is
// loaded, and an SVG or DXF dropped on an editor's drawing is read as its
// outline (as its File ▾ Import does); a banner says which while it is
// dragged, the drawing marked. Any other file is refused rather than
// opened by the browser in the page's place.
const dropBanner = document.getElementById("drop-banner");
let dropBannerTimer = null;
const DROP_EDITORS = [
  [bodyEditor, "body", "the body's outline"],
  [headstockEditor, "headstock", "the headstock's outline"],
  [inlayEditor, "inlay", "the marker"],
];

// The editor whose drawing a file is dragged over, or none.
function dropEditor(event) {
  return DROP_EDITORS.find(([editor]) => editor.svg?.contains(event.target)) || null;
}

function showDropHint(over) {
  dropBanner.textContent = over ? `Drop an SVG or DXF to import it as ${over[2]}` : "Drop a design (.json) to load it";
  dropBanner.hidden = false;
  for (const [editor] of DROP_EDITORS) editor.svg?.classList.toggle("file-target", editor === over?.[0]);
}

function hideDropHint() {
  dropBanner.hidden = true;
  for (const [editor] of DROP_EDITORS) editor.svg?.classList.remove("file-target");
}

document.addEventListener("dragover", (event) => {
  if (!event.dataTransfer?.types.includes("Files")) return;
  event.preventDefault();
  showDropHint(dropEditor(event));
  // Dragged on, the hint stays; dragged off (or dropped), it goes.
  clearTimeout(dropBannerTimer);
  dropBannerTimer = setTimeout(hideDropHint, 200);
});
document.addEventListener("drop", (event) => {
  if (!event.dataTransfer?.types.includes("Files")) return;
  event.preventDefault();
  hideDropHint();
  const [file] = event.dataTransfer.files;
  if (!file || loadDesignButton.disabled) return;  // the page not ready yet
  const over = dropEditor(event);
  const outline = /\.(svg|dxf)$/i.test(file.name);
  if (/\.json$/i.test(file.name)) openDesign(file);
  else if (outline && over) importOutline(over[1], file);
  else if (outline) setStatus(`Drop ${file.name} on an editor's drawing to import it`, "bad");
  else setStatus(`${file.name} is neither a design (.json) nor an outline (SVG, DXF)`, "bad");
});
// ---------------------------------------------------------------------------
// The tour: the basic path in a few steps, from an instrument to its NC and
// 3D files. Each step lights its part of the page up (the rest dimmed) with
// a card beside it, Next to go on; in the drawings a pointer shows what to
// do, moving a handle or a pickup now and then and putting it back (shown
// only: nothing is changed, and a press of the user's own stops it). It
// ends at Build, asking for it to be pressed. It runs once on the first
// visit, and again from Tour in the header.

const TOURED = "cncguitarwizard.toured";
const tourSpot = document.getElementById("tour-spot");
const tourCard = document.getElementById("tour-card");
const tourCursor = document.getElementById("tour-cursor");
const tourNext = document.getElementById("tour-next");
const tourSkip = document.getElementById("tour-skip");

const TOUR_STEPS = [
  {
    target: () => document.getElementById("instrument-rows"),
    title: "Choose the instrument",
    text: "A guitar, a 7- or 8-string or a bass, and its name: the files are named after it.",
  },
  {
    target: () => bodyEditor.svg,
    shown: () => !bodyEditor.panel.classList.contains("hidden"),
    title: "Shape the body",
    text: "Drag a round handle to shape the outline, or a pickup to move it. Start from, above the drawing, " +
      "gives you another body to begin with.",
    demo: (signal) => demoBody(signal),
  },
  {
    target: () => headstockEditor.svg,
    shown: () => !headstockEditor.panel.classList.contains("hidden"),
    title: "Shape the headstock",
    text: "The same here: drag its handles, and the tuner holes come along; drag a hole to slide it along the " +
      "edge. The inlays below work the same way.",
    demo: (signal) => demoHeadstock(signal),
  },
  {
    target: () => findSetting,
    title: "Fine-tune, if you like",
    text: "Every other value is in the list below: find one by its name. The defaults make a playable guitar, " +
      "so you can leave them as they are.",
  },
  {
    target: () => buildButton,
    title: "Build it",
    text: "Press Build 3D and CNC files: the NC programs for your CNC, the FreeCAD script for the 3D model and " +
      "plots of every toolpath appear, ready to download.",
  },
];

const tour = {
  steps: [],
  index: -1,
  frame: 0,
  controller: null,   // stops the step's showing in the drawing
  restore: null,      // puts back at once what the showing has moved
  cursorAt: null,
};

function startTour() {
  try {
    localStorage.setItem(TOURED, "1");
  } catch {
    // No storage: the tour may come again on the next visit.
  }
  endTour();
  tour.steps = TOUR_STEPS.filter((step) => !step.shown || step.shown());
  tourSpot.hidden = false;
  tourCard.hidden = false;
  showTourStep(0);
  const follow = () => {
    placeTour();
    tour.frame = requestAnimationFrame(follow);
  };
  follow();
}

function showTourStep(index) {
  stopTourDemo();
  tour.index = index;
  const step = tour.steps[index];
  const last = index === tour.steps.length - 1;
  document.getElementById("tour-title").textContent = step.title;
  document.getElementById("tour-text").textContent = step.text;
  document.getElementById("tour-count").textContent = `${index + 1} / ${tour.steps.length}`;
  tourNext.hidden = last;
  tourSkip.textContent = last ? "Close" : "Skip tour";
  step.target().scrollIntoView({ block: "center", behavior: "smooth" });
  (last ? tourSkip : tourNext).focus({ preventScroll: true });
  if (step.demo) {
    tour.controller = new AbortController();
    step.demo(tour.controller.signal);
  }
}

function endTour() {
  if (tour.index < 0) return;
  stopTourDemo();
  cancelAnimationFrame(tour.frame);
  tour.index = -1;
  tourSpot.hidden = true;
  tourCard.hidden = true;
}

// The light on the step's part and the card beside it, every frame: the
// page may be scrolling. The card goes under the part, else over it, else
// at the foot of the window.
function placeTour() {
  const box = tour.steps[tour.index].target().getBoundingClientRect();
  const pad = 6;
  Object.assign(tourSpot.style, {
    left: `${box.left - pad}px`, top: `${box.top - pad}px`,
    width: `${box.width + 2 * pad}px`, height: `${box.height + 2 * pad}px`,
  });
  const width = tourCard.offsetWidth, height = tourCard.offsetHeight, margin = 12;
  let top = box.bottom + pad + margin;
  if (top + height > innerHeight - margin) top = box.top - pad - margin - height;
  if (top < margin) top = innerHeight - height - margin;
  const left = Math.min(Math.max(margin, box.left), innerWidth - width - margin);
  Object.assign(tourCard.style, { left: `${left}px`, top: `${top}px` });
}

function stopTourDemo() {
  tour.controller?.abort();
  tour.controller = null;
  tour.restore?.();
  tour.restore = null;
  tour.cursorAt = null;
  tourCursor.hidden = true;
  tourCursor.classList.remove("pressed");
}

// A frame of the showing at a time, t from 0 to 1 (eased in and out);
// false once the step is left.
function tourAnimate(duration, frame, signal) {
  return new Promise((resolve) => {
    const start = performance.now();
    const tick = (now) => {
      if (signal.aborted) {
        resolve(false);
        return;
      }
      const t = Math.min(1, (now - start) / duration);
      frame(t < 0.5 ? 2 * t * t : 1 - (2 - 2 * t) ** 2 / 2);
      if (t < 1) requestAnimationFrame(tick);
      else resolve(true);
    };
    requestAnimationFrame(tick);
  });
}

function tourPause(ms, signal) {
  return new Promise((resolve) => {
    const timer = setTimeout(() => resolve(!signal.aborted), ms);
    signal.addEventListener("abort", () => {
      clearTimeout(timer);
      resolve(false);
    }, { once: true });
  });
}

function placeTourCursor([x, y]) {
  tour.cursorAt = [x, y];
  Object.assign(tourCursor.style, { left: `${x}px`, top: `${y}px` });
  tourCursor.hidden = false;
}

// The middle of elements on the page.
function centreOf(...elements) {
  const boxes = elements.map((element) => element.getBoundingClientRect());
  const left = Math.min(...boxes.map((b) => b.left)), right = Math.max(...boxes.map((b) => b.right));
  const top = Math.min(...boxes.map((b) => b.top)), bottom = Math.max(...boxes.map((b) => b.bottom));
  return [(left + right) / 2, (top + bottom) / 2];
}

// The pointer glides to a point (found each frame), from where it was or
// from the middle of the step's part.
function moveTourCursor(to, signal) {
  const from = tour.cursorAt || centreOf(tour.steps[tour.index].target());
  return tourAnimate(650, (t) => {
    const [x, y] = to();
    placeTourCursor([from[0] + (x - from[0]) * t, from[1] + (y - from[1]) * t]);
  }, signal);
}

// Press, move out and back, let go: the shape of every showing.
async function tourDrag(at, drag, signal) {
  if (!(await moveTourCursor(at, signal))) return false;
  tourCursor.classList.add("pressed");
  const done = await tourAnimate(700, drag, signal)
    && await tourPause(250, signal)
    && await tourAnimate(700, (t) => drag(1 - t), signal);
  tourCursor.classList.remove("pressed");
  tour.restore?.();
  tour.restore = null;
  return done;
}

const pickAny = (items) => items[Math.floor(Math.random() * items.length)];

// The body: a handle of the outline pulled out and back, then a pickup
// slid along the neck and back.
async function demoBody(signal) {
  const editor = bodyEditor;
  // Shown once the step has scrolled into view and the drawing is laid out.
  do {
    if (!(await tourPause(700, signal))) return;
  } while (!editor.layout || !editor.handles?.length);
  for (;;) {
    const index = Math.floor(Math.random() * editor.points.length);
    const original = [...editor.points[index]];
    const start = editor.widen(original);
    const shown = editor.points.map((point) => editor.widen(point));
    const middle = [0, 1].map((axis) => shown.reduce((sum, point) => sum + point[axis], 0) / shown.length);
    const away = [start[0] - middle[0], start[1] - middle[1]];
    const length = Math.hypot(...away) || 1;
    const out = away.map((value) => (value / length) * 14);
    tour.restore = () => {
      editor.points[index] = [...original];
      editor.showPoint(index, start);
    };
    const handle = () => centreOf(editor.handles[index]);
    const pulled = await tourDrag(handle, (t) => {
      const point = [start[0] + out[0] * t, start[1] + out[1] * t];
      editor.points[index] = editor.unwiden(point);
      editor.showPoint(index, point);
      placeTourCursor(handle());
    }, signal);
    if (!pulled || !(await tourPause(500, signal))) return;

    const groups = [...new Set([...editor.svg.querySelectorAll('[data-group^="pickup:"]')].map((n) => n.dataset.group))];
    if (groups.length) {
      const members = [...editor.svg.querySelectorAll(`[data-group="${pickAny(groups)}"]`)];
      const transforms = members.map((member) => member.getAttribute("transform"));
      tour.restore = () => members.forEach((member, i) => {
        if (transforms[i] === null) member.removeAttribute("transform");
        else member.setAttribute("transform", transforms[i]);
      });
      const along = (Math.random() < 0.5 ? -1 : 1) * 22;
      const slid = await tourDrag(() => centreOf(...members), (t) => {
        for (const member of members) member.setAttribute("transform", `translate(${along * t} 0)`);
        placeTourCursor(centreOf(...members));
      }, signal);
      if (!slid) return;
    }
    if (!(await tourPause(900, signal))) return;
  }
}

// The headstock: a handle of one edge pulled out and back.
async function demoHeadstock(signal) {
  const editor = headstockEditor;
  do {
    if (!(await tourPause(700, signal))) return;
  } while (!editor.edgeHandles);
  for (;;) {
    const side = pickAny(["bass", "treble"]);
    const edge = editor.edges[side];
    if (edge.length < 2) return;
    const index = Math.floor(Math.random() * (edge.length - 1));  // not the tip's corner
    const [d, h] = edge[index];
    const sign = editor.sign(side);
    const edges = { bass: editor.edges.bass.map((p) => [...p]), treble: editor.edges.treble.map((p) => [...p]) };
    const tip = editor.tip.map((p) => [...p]);
    const handle = editor.edgeHandles[side][index];
    const insets = editor.holeInsets();
    tour.restore = () => {
      editor.edges.bass = edges.bass.map((p) => [...p]);
      editor.edges.treble = edges.treble.map((p) => [...p]);
      editor.tip = tip.map((p) => [...p]);
      editor.showEdges();
      editor.layout.holes.forEach((hole, i) => {
        hole.y = insets[i].y;
        editor.showHole(i);
      });
      handle.setAttribute("cx", -d);
      handle.setAttribute("cy", -sign * h);
    };
    const pulled = await tourDrag(() => centreOf(handle), (t) => {
      editor.place(side, index, [-d, sign * (h + 6 * t)]);
      editor.showEdges();
      editor.followEdges(insets);
      const [nd, nh] = editor.edges[side][index];
      handle.setAttribute("cx", -nd);
      handle.setAttribute("cy", -sign * nh);
      placeTourCursor(centreOf(handle));
    }, signal);
    if (!pulled || !(await tourPause(900, signal))) return;
  }
}

tourNext.addEventListener("click", () => showTourStep(tour.index + 1));
tourSkip.addEventListener("click", endTour);
document.getElementById("start-tour").addEventListener("click", startTour);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && tour.index >= 0 && !document.querySelector("dialog[open]")) endTour();
});
// A press in a drawing of the user's own stops the showing there first,
// so their drag starts from the drawing as it is.
for (const editor of [bodyEditor, headstockEditor]) {
  editor.svg.addEventListener("pointerdown", stopTourDemo, true);
}

showAdvanced.addEventListener("change", applyAdvancedToggle);
findSetting.addEventListener("input", applyFormFilter);
// In Find a setting, Enter goes to the first setting found (its value
// selected, ready to be typed over) and Escape clears the search.
findSetting.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    const first = [...form.querySelectorAll(".field.match")].find((row) => row.offsetParent !== null);
    const control = first?.querySelector("input, select");
    if (!control) return;
    event.preventDefault();
    control.focus();
    if (control.tagName === "INPUT") control.select();
  } else if (event.key === "Escape" && findSetting.value) {
    event.preventDefault();
    findSetting.value = "";
    applyFormFilter();
  }
});
// "/" anywhere but a field goes to Find a setting.
document.addEventListener("keydown", (event) => {
  if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey) return;
  if (event.target.closest?.("input, select, textarea, [contenteditable]")) return;
  if (document.querySelector("dialog[open]")) return;
  event.preventDefault();
  findSetting.focus();
  findSetting.select();
});
changedOnly.addEventListener("change", applyFormFilter);
// A value changed (or set back) while only the changed ones show: shown,
// or left out, once the change is done.
form.addEventListener("change", () => {
  if (changedOnly.checked) applyFormFilter();
});
boot();
