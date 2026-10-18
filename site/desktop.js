"use strict";
// The application like UI, tried beside the Classic UI: a menu bar at
// the top as in a desktop application (File, Edit, Design, Settings,
// Build, View, Help) and one page shown at a time — the instrument, an
// editor, the settings or the result — instead of one long page to
// scroll. Nothing is built twice: the Classic UI's own parts are shown
// page by page, and the menus press its own buttons, so app.js runs as
// ever.
//
// A new visitor gets the application like UI, and dark mode; its View
// menu goes to the Classic UI (whose header comes back: Application like
// UI). The choice is kept in this browser, and ?layout=desktop or
// ?layout=classic in the address chooses one too. Dark mode, either way,
// is a choice of its own (View > Dark mode, the Classic UI header's
// Light mode / Dark mode), kept too; index.html sets it as the page loads.

(() => {
  const LAYOUT = "cgw-layout";
  const PAGE = "cgw-layout-page";

  function stored(key) {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;  // no storage (a private window)
    }
  }

  function store(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {
      // No storage: the choice lasts until the page is left.
    }
  }

  function useLayout(layout) {
    store(LAYOUT, layout);
    const here = new URL(location.href);
    here.searchParams.delete("layout");
    location.replace(here.href);
  }

  // Dark mode: the page's colours are tokens (index.html) that its dark
  // theme sets afresh.
  const THEME = "cgw-theme";
  const isDark = () => document.documentElement.dataset.theme === "dark";
  function setDark(dark) {
    if (dark) document.documentElement.dataset.theme = "dark";
    else delete document.documentElement.dataset.theme;
    store(THEME, dark ? "dark" : "light");
  }

  const asked = new URL(location.href).searchParams.get("layout");
  if (asked === "desktop" || asked === "classic") store(LAYOUT, asked);
  const byId = (id) => document.getElementById(id);

  if ((asked || stored(LAYOUT) || "desktop") === "classic") {
    // The Classic UI: buttons in its header to try the application like
    // UI and to turn dark mode on or off.
    const tryIt = document.createElement("button");
    tryIt.className = "secondary keys-button";
    tryIt.type = "button";
    tryIt.textContent = "Application like UI";
    tryIt.title = "Try the page as a desktop application: menus at the top, one page at a time (View > Classic UI comes back)";
    tryIt.addEventListener("click", () => useLayout("desktop"));
    const dark = document.createElement("button");
    dark.className = "secondary keys-button";
    dark.type = "button";
    const syncDark = () => {
      dark.textContent = isDark() ? "Light mode" : "Dark mode";
      dark.setAttribute("aria-pressed", String(isDark()));
      dark.title = isDark() ? "Back to the light colours" : "The page in dark colours (the drawings stay on light paper)";
    };
    dark.addEventListener("click", () => {
      setDark(!isDark());
      syncDark();
    });
    syncDark();
    byId("show-keys").after(tryIt, dark);
    return;
  }

  const MAC = /Mac|iPhone|iPad/.test(navigator.platform);
  const KEY = MAC ? "⌘" : "Ctrl+";

  // ---- the look -----------------------------------------------------------
  const style = document.createElement("style");
  style.textContent = `
    body.desktop-ui { padding: 34px 0 28px; }
    body.desktop-ui > header, body.desktop-ui #jump, body.desktop-ui #build-float { display: none !important; }
    body.desktop-ui main { display: block; min-height: calc(100vh - 62px); }
    body.desktop-ui aside { display: block; position: static; max-height: none; overflow: visible;
      border: 0; padding: 0; }
    body.desktop-ui section.results { padding: 0; }
    body.desktop-ui .desk-page { max-width: 1180px; margin: 0 auto; padding: 18px 22px 30px; }
    body.desktop-ui #error { max-width: 1180px; margin: 12px auto 0; }
    @media screen {
      body.desktop-ui [data-page]:not(.page-on) { display: none !important; }
      body.desktop-ui #output [data-sub]:not(.sub-on):not([data-sub="all"]) { display: none !important; }
      body.desktop-ui #form:not(.filtering) > details.group:not(.group-on) { display: none; }
    }
    @media print {
      body.desktop-ui { padding: 0; }
      body.desktop-ui :is(.menubar, .statusbar, .desk-tabs, .desk-groups) { display: none !important; }
    }

    .menubar { position: fixed; top: 0; left: 0; right: 0; z-index: 50; height: 34px;
      display: flex; align-items: stretch; gap: 2px; padding: 0 10px;
      background: var(--chrome); border-bottom: 1px solid var(--line); font-size: 13.5px; user-select: none; }
    .menubar .brand { display: flex; align-items: center; padding: 0 12px 0 4px; font-weight: 700; }
    .menubar .menu-title { display: flex; align-items: center; padding: 0 10px; border: 0; border-radius: 5px;
      margin: 4px 0; background: none; color: var(--ink); font: inherit; cursor: default; }
    .menubar .menu-title:hover, .menubar .menu-title.open { background: var(--hover); }
    .menubar .spacer { flex: 1 1 auto; }
    .menubar .bar-build { margin: 4px 0; padding: 0 14px; font-size: 13px; }

    .menu-pop { position: fixed; z-index: 60; min-width: 230px; padding: 5px; background: var(--panel);
      border: 1px solid var(--line); border-radius: 8px; box-shadow: 0 8px 24px rgba(40, 30, 20, 0.18); }
    .menu-pop[hidden] { display: none; }
    .menu-pop button { display: flex; width: 100%; gap: 18px; justify-content: space-between; align-items: center;
      padding: 5px 10px; border: 0; border-radius: 5px; background: none; color: var(--ink);
      font: inherit; font-weight: 400; text-align: left; cursor: default; }
    .menu-pop button:hover:not(:disabled), .menu-pop button:focus-visible { background: var(--accent); color: #fff; outline: none; }
    .menu-pop button:disabled { color: var(--muted); opacity: 0.55; }
    .menu-pop button .key { color: var(--muted); font-size: 12px; }
    .menu-pop button:hover:not(:disabled) .key { color: #f4e6d6; }
    .menu-pop button .tick { display: inline-block; width: 16px; }
    .menu-pop hr { border: 0; border-top: 1px solid var(--line); margin: 4px 6px; }
    .menu-pop .menu-label { padding: 4px 10px 2px; color: var(--muted); font-size: 11.5px; }

    .statusbar { position: fixed; bottom: 0; left: 0; right: 0; z-index: 50; height: 28px;
      display: flex; align-items: center; gap: 14px; padding: 0 14px;
      background: var(--chrome); border-top: 1px solid var(--line); color: var(--muted); font-size: 12px; }
    .statusbar .where { flex: none; font-weight: 600; color: var(--ink); }
    .statusbar #status { flex: 1 1 auto; min-width: 0; margin: 0; white-space: nowrap; overflow: hidden;
      text-overflow: ellipsis; }
    .statusbar #progress { flex: 0 1 360px; margin: 0; display: flex; align-items: center; gap: 8px; }
    .statusbar #progress .bar { flex: 0 0 160px; }
    .statusbar #progress .label { min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .statusbar #progress.hidden { display: none; }
    @media (max-width: 900px) {
      .menubar .brand { display: none; }
      .menubar .menu-title { padding: 0 8px; }
    }

    .desk-tabs { display: flex; gap: 4px; margin: 0 0 14px; border-bottom: 1px solid var(--line); }
    .desk-tabs button { border: 0; border-radius: 6px 6px 0 0; padding: 6px 14px; background: none;
      color: var(--muted); font: inherit; font-weight: 600; }
    .desk-tabs button.on { background: var(--panel); color: var(--ink); border: 1px solid var(--line); border-bottom-color: var(--panel);
      margin-bottom: -1px; }

    body.desktop-ui .settings-page { display: grid; grid-template-columns: 220px 1fr; gap: 0 22px; align-items: start; }
    .desk-groups { position: sticky; top: 46px; display: flex; flex-direction: column; gap: 1px;
      max-height: calc(100vh - 100px); overflow-y: auto; }
    .desk-groups button { border: 0; border-radius: 6px; padding: 6px 10px; background: none; color: var(--ink);
      font: inherit; text-align: left; font-weight: 500; }
    .desk-groups button:hover { background: var(--hover); }
    .desk-groups button.on { background: var(--accent); color: #fff; }
    .desk-groups button .count { float: right; font-size: 11.5px; opacity: 0.8; }
    body.desktop-ui .settings-page details.group[open] > summary { top: 34px; }
    .menubar .bar-build.busy { background: var(--panel); color: var(--accent); border: 1px solid var(--accent);
      font-variant-numeric: tabular-nums; }

    .desk-build { padding-bottom: 0 !important; }
    .desk-build .card { padding: 16px 18px; background: var(--panel); border: 1px solid var(--line); border-radius: 10px; }
    .desk-build .head { display: flex; align-items: center; gap: 12px; }
    .desk-build .head h2 { margin: 0; font-size: 19px; }
    .desk-build .head .left { margin-left: auto; color: var(--muted); }
    .desk-build .head .time { color: var(--muted); font-variant-numeric: tabular-nums; }
    .desk-build .icon { flex: none; width: 22px; height: 22px; display: grid; place-items: center;
      border-radius: 50%; font-weight: 700; color: #fff; }
    .desk-build.running .icon { border: 3px solid var(--hover); border-top-color: var(--accent);
      animation: desk-spin 0.9s linear infinite; }
    .desk-build.done .icon { background: var(--ok); }
    .desk-build.failed .icon { background: var(--bad); }
    @keyframes desk-spin { to { transform: rotate(360deg); } }
    .desk-build .meter { height: 12px; margin: 14px 0 8px; background: var(--hover); border-radius: 6px; overflow: hidden; }
    /* No easing: the page paints only between the build's steps, so the
       bar has to be where it is at once. */
    .desk-build .meter .fill { height: 100%; width: 0; background: var(--accent); }
    .desk-build.done .meter .fill { background: var(--ok); }
    .desk-build.failed .meter .fill { background: var(--bad); }
    .desk-build .now { margin: 0; font-size: 15px; font-weight: 600; }
    .desk-build .about { margin: 4px 0 0; }
    .desk-build details { margin: 12px 0 0; border: 0; background: none; }
    .desk-build details summary { padding: 0; font-weight: 500; color: var(--muted); }
    .desk-build ol { margin: 6px 0 0; padding: 0; list-style: none; display: grid;
      grid-template-columns: auto 1fr auto; gap: 2px 10px; font-size: 13px; }
    .desk-build li { display: contents; }
    .desk-build li span:last-child { color: var(--muted); font-variant-numeric: tabular-nums; text-align: right; }
    .desk-build li.running span { font-weight: 600; }
    .desk-build li.pending span { color: var(--muted); }
    .menubar .find { flex: 0 1 240px; min-width: 120px; margin: 5px 10px 5px 0; padding: 0 10px;
      border: 1px solid var(--line); border-radius: 6px; background: var(--panel); color: var(--ink); font: inherit; }
    .find-pop { position: fixed; z-index: 60; width: min(560px, calc(100vw - 20px)); max-height: 72vh; overflow-y: auto;
      padding: 6px; background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
      box-shadow: 0 8px 24px rgba(40, 30, 20, 0.22); }
    .find-pop[hidden] { display: none; }
    .find-pop .found { display: grid; grid-template-columns: 1fr auto; gap: 2px 12px; align-items: center;
      padding: 7px 8px; border-radius: 6px; }
    .find-pop .found + .found { border-top: 1px solid var(--line); }
    .find-pop .found .name { font-weight: 600; }
    .find-pop .found .name mark { background: var(--mark); color: inherit; border-radius: 2px; }
    .find-pop .found .meaning { grid-column: 1 / -1; color: var(--muted); font-size: 12px; overflow: hidden;
      text-overflow: ellipsis; white-space: nowrap; }
    .find-pop .found .control input[type=text], .find-pop .found .control input[type=number],
    .find-pop .found .control select { width: 150px; padding: 3px 6px; border: 1px solid var(--line);
      border-radius: 4px; background: var(--panel); color: var(--ink); font: inherit; font-size: 12.5px; }
    .find-pop .found .control .changed { border-color: var(--accent); background: var(--tint); }
    .find-pop .found .places { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 4px 12px; font-size: 12.5px; }
    .find-pop .found .places button { padding: 0; border: 0; background: none; color: var(--accent);
      font: inherit; font-weight: 600; cursor: pointer; }
    .find-pop .found .places button:hover { text-decoration: underline; }
    .find-pop .note { margin: 6px 8px; }
    @media (max-width: 900px) { .menubar .find { flex-basis: 150px; } }
    body.desktop-ui #intro { max-width: 760px; }
    body.desktop-ui .aside-top { max-width: 560px; }
  `;
  document.head.appendChild(style);
  document.body.classList.add("desktop-ui");

  // ---- the pages ----------------------------------------------------------
  // The classic page's parts, each on one page: the instrument with its
  // style and design file, the settings, each editor and the result.
  // The build's own panel, at the head of the result page (see "a build,
  // in sight" below).
  const buildPanel = document.createElement("div");
  buildPanel.id = "desk-build";
  buildPanel.className = "desk-build hidden";
  buildPanel.setAttribute("aria-live", "polite");
  buildPanel.innerHTML = `
    <div class="card">
      <div class="head"><span class="icon" aria-hidden="true"></span><h2 class="title"></h2><span class="left"></span><span class="time"></span></div>
      <div class="meter"><div class="fill"></div></div>
      <p class="now"></p>
      <p class="about note"></p>
      <details class="fold"><summary class="count"></summary><ol class="steps"></ol></details>
    </div>`;
  byId("output").before(buildPanel);

  const PAGES = [
    { id: "design", title: "Instrument", parts: ["#intro", ".aside-top", "body > footer"] },
    { id: "body", title: "Body", parts: ["#body-editor"] },
    { id: "headstock", title: "Headstock", parts: ["#headstock-editor"] },
    { id: "inlays", title: "Inlays", parts: ["#inlay-editor"] },
    { id: "settings", title: "Settings", parts: [".aside-form"] },
    { id: "result", title: "Result", parts: ["#desk-build", "#output"] },
  ];
  const pageOf = new Map(PAGES.map((page) => [page.id, page]));
  for (const page of PAGES) {
    for (const selector of page.parts) {
      const part = document.querySelector(selector);
      if (!part) continue;
      part.dataset.page = page.id;
      part.classList.add("desk-page");
    }
  }
  const settingsPage = document.querySelector(".aside-form");
  settingsPage.classList.add("settings-page");

  // A page that is not there now (no headstock to draw, no result yet).
  function available(id) {
    return [...document.querySelectorAll(`[data-page="${id}"]`)]
      .some((part) => !part.classList.contains("hidden"));
  }

  let current = null;
  function showPage(id) {
    if (!pageOf.has(id)) id = "design";
    current = id;
    for (const part of document.querySelectorAll("[data-page]")) {
      part.classList.toggle("page-on", part.dataset.page === id);
    }
    where.textContent = pageOf.get(id).title;
    store(PAGE, id);
    window.scrollTo({ top: 0 });
    // A drawing laid out while hidden fits itself again once shown.
    window.dispatchEvent(new Event("resize"));
  }

  // ---- the result's own tabs ----------------------------------------------
  // Summary, Downloads (and the simulator), Plan view and Toolpaths, one at
  // a time; the build's title and its "no longer the design's" note on all.
  const output = byId("output");
  const SUBS = [
    ["summary", "Summary"],
    ["files", "Downloads"],
    ["plan", "Plan view"],
    ["toolpaths", "Toolpaths"],
  ];
  let sub = "all";
  for (const child of output.children) {
    const heading = child.tagName === "H2" ? child.textContent.trim() : "";
    if (child.classList.contains("summary-head")) sub = "summary";
    else if (heading.startsWith("Downloads")) sub = "files";
    else if (heading.startsWith("Plan view")) sub = "plan";
    else if (heading.startsWith("Toolpaths")) sub = "toolpaths";
    child.dataset.sub = sub;
  }
  const tabs = document.createElement("div");
  tabs.className = "desk-tabs";
  tabs.dataset.sub = "all";
  output.prepend(tabs);
  const subButtons = new Map();
  for (const [id, title] of SUBS) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = title;
    button.addEventListener("click", () => showSub(id));
    tabs.appendChild(button);
    subButtons.set(id, button);
  }
  function showSub(id) {
    for (const child of output.children) child.classList.toggle("sub-on", child.dataset.sub === id);
    for (const [key, button] of subButtons) button.classList.toggle("on", key === id);
    window.dispatchEvent(new Event("resize"));
  }
  showSub("summary");

  // ---- the settings, a group at a time --------------------------------------
  const form = byId("form");
  const groupList = document.createElement("nav");
  groupList.className = "desk-groups";
  groupList.setAttribute("aria-label", "Setting groups");
  settingsPage.prepend(groupList);
  // The form's notes and search over the groups, beside the list.
  const settingsMain = document.createElement("div");
  for (const child of [...settingsPage.children]) {
    if (child !== groupList) settingsMain.appendChild(child);
  }
  settingsPage.appendChild(settingsMain);

  let groupTitle = null;
  const groups = () => [...form.querySelectorAll(":scope > details.group")];
  function showGroup(title) {
    const all = groups();
    const chosen = all.find((group) => group.dataset.title === title) || all[0];
    if (!chosen) return;
    groupTitle = chosen.dataset.title;
    for (const group of all) group.classList.toggle("group-on", group === chosen);
    if (!chosen.open) chosen.open = true;
    listGroups();
  }
  function listGroups() {
    groupList.replaceChildren();
    for (const group of groups()) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = group.dataset.title;
      const changed = group.querySelectorAll("input.changed, select.changed").length;
      if (changed) {
        const count = document.createElement("span");
        count.className = "count";
        count.textContent = String(changed);
        count.title = `${changed} changed from the default`;
        button.appendChild(count);
      }
      button.classList.toggle("on", group.dataset.title === groupTitle);
      button.addEventListener("click", () => {
        showGroup(group.dataset.title);
        window.scrollTo({ top: 0 });
      });
      groupList.appendChild(button);
    }
  }
  // The form is laid out afresh (an instrument, a reset): the group shown
  // stays the one chosen.
  new MutationObserver(() => showGroup(groupTitle)).observe(form, { childList: true });
  form.addEventListener("change", listGroups);
  showGroup(null);

  // ---- going to what the page points at -----------------------------------
  // app.js reveals what it scrolls to or selects (the result once built, a
  // setting found, the tour's next stop): its page, result tab or group.
  function reveal(element) {
    if (!element || !element.closest) return;
    const part = element.closest("[data-page]");
    if (part && part.dataset.page !== current) showPage(part.dataset.page);
    const inResult = element.closest("#output [data-sub]");
    if (inResult && inResult.dataset.sub !== "all") showSub(inResult.dataset.sub);
    const group = element.closest("#form > details.group");
    if (group && group.dataset.title !== groupTitle) showGroup(group.dataset.title);
  }
  window.cncgwLayout = { reveal, showPage };
  // Anything selected on a page not shown (a key that moves the focus).
  document.addEventListener("focusin", (event) => {
    if (!event.target.closest(".menubar, .menu-pop")) reveal(event.target);
  });

  // ---- the menu bar and status bar ------------------------------------------
  const bar = document.createElement("nav");
  bar.className = "menubar";
  bar.setAttribute("aria-label", "Menus");
  const brand = document.createElement("span");
  brand.className = "brand";
  brand.textContent = "CNCguitarwizard";
  bar.appendChild(brand);
  const status = byId("status");
  const progressBox = byId("progress");
  // The build running now (see "a build, in sight"), or null.
  let building = null;
  const buildButton = byId("build");
  const barBuild = document.createElement("button");
  barBuild.type = "button";
  barBuild.className = "bar-build";
  barBuild.textContent = "Build";
  barBuild.title = `Build the 3D and CNC files (${KEY}Enter)`;
  // While a build runs it says how far it is, and goes to it.
  barBuild.addEventListener("click", () => {
    if (building) showPage("result");
    else buildButton.click();
  });
  const syncBuild = () => {
    barBuild.disabled = buildButton.disabled && !building;
    barBuild.classList.toggle("busy", Boolean(building));
    barBuild.textContent = building ? `Building… ${building.percent}%` : "Build";
  };
  new MutationObserver(syncBuild).observe(buildButton, { attributes: true, attributeFilter: ["disabled"] });

  const statusBar = document.createElement("div");
  statusBar.className = "statusbar";
  const where = document.createElement("span");
  where.className = "where";
  statusBar.append(where, status, progressBox);

  // ---- a build, in sight ----------------------------------------------------
  // Build opens the result page at once, a panel at its head saying what
  // the build is doing: its steps, each with its time once passed and its
  // likely time before, the one running, how far it is, how long it has
  // taken and about how long is left — then how it ended, the result under
  // it. app.js's own progress (its label "3/8 · Planning the neck
  // toolpaths" and its bar), its Build button ("busy" while it runs) and
  // its "cgw-build-stages" (every step, as the build starts) tell it.
  //
  // A step's likely time is this browser's own from its builds so far
  // (STEP_TIMES), else a typical build's (TYPICAL_STEPS), and once a step
  // is done all are scaled by how quick this build has been so far
  // (pace): after the first step the rest are about known.
  const TYPICAL_STEPS = {
    "Building the geometry": 0.6,
    "Planning the body toolpaths": 7.8,
    "Planning the neck toolpaths": 29.4,
    "Planning the fretboard toolpaths": 0.9,
    "Planning the cover plates": 0.5,
    "Writing G-code and toolpath previews": 0.6,
    "Writing the DXF outlines": 0.1,
    "Writing the FreeCAD script and report": 0.2,
  };
  const STEP_TIMES = "cgw-step-times";
  const progressLabel = progressBox.querySelector(".label");
  let ticker = null;
  const since = (from) => (performance.now() - from) / 1000;
  const panelPart = (selector) => buildPanel.querySelector(selector);

  function learnedTimes() {
    try {
      return JSON.parse(stored(STEP_TIMES) || "{}");
    } catch {
      return {};  // nothing readable kept
    }
  }

  // A step's time in a build like the last ones, before this one's pace.
  function baseTime(label) {
    return building.learned[label] ?? TYPICAL_STEPS[label] ?? 1.0;
  }

  // How much slower (above 1) or quicker this build runs than its steps'
  // base times say, from the steps done; 1 before the first is.
  function pace() {
    const taken = building.steps.reduce((sum, step) => sum + step.seconds, 0);
    const expected = building.steps.reduce((sum, step) => sum + baseTime(step.text), 0);
    if (!building.steps.length || expected < 0.05) return 1;
    return Math.min(5, Math.max(0.2, taken / expected));
  }

  const likely = (label) => baseTime(label) * pace();

  function about(value) {
    if (value < 1) return "under 1 s";
    if (value < 60) return `about ${Math.round(value)} s`;
    const minutes = Math.floor(value / 60);
    const rest = Math.round(value - 60 * minutes);
    return `about ${minutes} min${rest ? ` ${rest} s` : ""}`;
  }

  // The steps not started yet (every step known once the build has said).
  function pending() {
    const started = building.steps.length + (building.current ? 1 : 0);
    return building.stages.slice(started);
  }

  function startWatch() {
    building = {
      started: performance.now(),
      steps: [],
      current: null,
      stages: [],
      percent: 0,
      learned: learnedTimes(),
    };
    buildPanel.className = "desk-build desk-page running";
    buildPanel.classList.toggle("page-on", true);
    const name = byId("guitar-name").value.trim() || "Prototype001";
    panelPart(".title").textContent = `Building ${name}…`;
    panelPart(".now").textContent = "Reading the design…";
    panelPart(".about").textContent = "The FreeCAD script, the G-code for every part, their plots and "
      + "the drawings are made here in your browser, step by step.";
    panelPart(".left").textContent = "";
    panelPart(".meter .fill").style.width = "0%";
    panelPart(".fold").open = true;
    listSteps();
    showPage("result");
    ticker = setInterval(tick, 200);
    tick();
    syncBuild();
  }

  function onStages(event) {
    if (!building) return;
    building.stages = [...event.detail];
    building.total = building.stages.length;
    showEstimate();
  }

  function onProgress() {
    if (!building) return;
    const found = /^(\d+)\/(\d+) · (.*)$/.exec(progressLabel.textContent.trim());
    if (!found) return;
    const [, index, total, text] = found;
    const now = performance.now();
    const current = building.current;
    if (current && (text === "done" || current.text !== text)) {
      building.steps.push({ text: current.text, seconds: (now - current.started) / 1000 });
    }
    building.total = Number(total);
    building.current = text === "done" ? null : { index: Number(index), text, started: now };
    showEstimate();
  }

  // How far the build is (by its steps' likely times, so the long ones
  // count for more), the step running, about how long is left, the list.
  function showEstimate() {
    const done = building.steps.reduce((sum, step) => sum + baseTime(step.text), 0);
    const all = building.stages.length
      ? building.stages.reduce((sum, label) => sum + baseTime(label), 0)
      : 0;
    building.percent = all
      ? Math.round((100 * done) / all)
      : Math.round((100 * building.steps.length) / (building.total || 1));
    panelPart(".meter .fill").style.width = `${building.percent}%`;
    const current = building.current;
    panelPart(".now").textContent = current
      ? `Step ${current.index} of ${building.total}: ${current.text} — ${about(likely(current.text))}`
      : building.steps.length
        ? "Putting the files together…"
        : "Reading the design…";
    const left = [...(current ? [current.text] : []), ...pending()]
      .reduce((sum, label) => sum + likely(label), 0);
    panelPart(".left").textContent = building.stages.length && current ? `${about(left)} left · ` : "";
    listSteps();
    tick();
    syncBuild();
  }

  function listSteps() {
    const list = panelPart(".steps");
    list.replaceChildren();
    const row = (mark, text, time, kind) => {
      const item = document.createElement("li");
      if (kind) item.className = kind;
      for (const value of [mark, text, time]) {
        const cell = document.createElement("span");
        cell.textContent = value;
        item.appendChild(cell);
      }
      list.appendChild(item);
    };
    for (const step of building.steps) row("✓", step.text, `${step.seconds.toFixed(1)} s`, "");
    if (building.current) {
      row("…", building.current.text, about(likely(building.current.text)), "running");
    }
    for (const label of pending()) row("·", label, about(likely(label)), "pending");
    panelPart(".count").textContent = building.total
      ? `${building.steps.length} of ${building.total} steps`
      : "Steps";
  }

  function tick() {
    if (!building) return;
    panelPart(".time").textContent = `${since(building.started).toFixed(1)} s`;
  }

  // A build that ran through teaches the next its steps' times: each the
  // mean of what it took and what was kept.
  function learnTimes() {
    const learned = building.learned;
    for (const step of building.steps) {
      const kept = learned[step.text];
      learned[step.text] = Math.round(10 * (kept === undefined ? step.seconds : (kept + step.seconds) / 2)) / 10;
    }
    store(STEP_TIMES, JSON.stringify(learned));
  }

  function endWatch() {
    clearInterval(ticker);
    const built = status.className === "ok";
    const name = byId("guitar-name").value.trim() || "Prototype001";
    buildPanel.classList.remove("running");
    buildPanel.classList.add(built ? "done" : "failed");
    panelPart(".icon").textContent = built ? "✓" : "✕";
    panelPart(".time").textContent = `${since(building.started).toFixed(1)} s`;
    panelPart(".left").textContent = "";
    if (built) {
      learnTimes();
      panelPart(".title").textContent = `${name} is built`;
      panelPart(".meter .fill").style.width = "100%";
      panelPart(".now").textContent = `${status.textContent}: the summary is below, every file under Downloads.`;
      panelPart(".about").textContent = "Build again after a change: the result then says it is no longer the design's.";
      panelPart(".fold").open = false;
    } else {
      panelPart(".title").textContent = "The build stopped";
      panelPart(".now").textContent = building.current
        ? `${status.textContent} at step ${building.current.index} of ${building.total}: ${building.current.text}.`
        : `${status.textContent}.`;
      panelPart(".about").textContent = "What went wrong is said above; change that and build again.";
    }
    building = null;
    syncBuild();
  }

  new MutationObserver(() => {
    const busy = buildButton.classList.contains("busy");
    if (busy && !building) startWatch();
    else if (!busy && building) endWatch();
  }).observe(buildButton, { attributes: true, attributeFilter: ["class"] });
  new MutationObserver(onProgress).observe(progressLabel, { childList: true, characterData: true, subtree: true });
  document.addEventListener("cgw-build-stages", onStages);
  syncBuild();

  // ---- find a setting, from anywhere ------------------------------------------
  // The bar's own search: each setting whose name or meaning holds every
  // word typed (as the form's own search finds them), with its control
  // to set it there and then — a copy, as an editor's Settings holds one —
  // and a link to each page it is on: its editor's Settings (Design ›
  // Body) when one shows it there, else its group (Settings › Body).
  const FIND_LIMIT = 40;
  // Where an editor's Settings put their copies, and the page each is on.
  const EDITOR_PAGES = {
    "body-editor-options": ["body", "Design › Body"],
    "headstock-editor-options": ["headstock", "Design › Headstock"],
    "inlay-editor-options": ["inlays", "Design › Inlays"],
    "easy-options": ["design", "Instrument"],
  };
  const findBox = document.createElement("input");
  findBox.type = "search";
  findBox.className = "find";
  findBox.placeholder = "Find a setting… (/)";
  findBox.setAttribute("aria-label", "Find a setting");
  findBox.autocomplete = "off";
  const findPop = document.createElement("div");
  findPop.className = "find-pop";
  findPop.hidden = true;

  // The words typed, as the form's search reads them.
  const findWords = () => findBox.value.toLowerCase().replace(/_/g, " ").split(/\s+/).filter(Boolean);

  // A form row's text the words are looked for in: its name, field name
  // and meaning.
  function rowText(row) {
    const control = row.querySelector("input, select");
    const label = row.querySelector("label");
    return [label?.dataset.label ?? label?.textContent, control?.dataset.name, row.title]
      .join(" ").toLowerCase().replace(/_/g, " ");
  }

  // The places a setting is set: each editor's Settings that holds a
  // copy of it (shown), and its group in the form while its row shows
  // there (a copy shown in an editor takes it out of the form).
  function places(row, original) {
    const found = [];
    const name = original.dataset.name;
    for (const [holder, [page, title]] of Object.entries(EDITOR_PAGES)) {
      const copy = byId(`${holder}.${name}`);
      if (copy && available(page)) found.push({ title, go: () => goToCopy(page, copy) });
    }
    const group = row.closest("#form > details.group");
    if (group && !row.classList.contains("mirrored")) {
      found.push({ title: `Settings › ${group.dataset.title}`, go: () => goToField(original) });
    }
    return found;
  }

  function goToCopy(page, copy) {
    showPage(page);
    const fold = copy.closest("details");
    if (fold) fold.open = true;
    copy.scrollIntoView({ block: "center" });
    copy.focus();
  }

  // A control that sets the form's own, as an editor's copy does.
  function proxy(original) {
    const copy = original.cloneNode(true);
    copy.removeAttribute("id");
    delete copy.dataset.set;
    delete copy.dataset.name;
    if (copy.type === "checkbox") copy.checked = original.checked;
    else copy.value = original.value;
    const pass = (event) => {
      if (copy.tagName === "INPUT" && copy.type !== "checkbox") {
        if (valueProblem(copy)) {
          if (event.type === "change") copy.classList.add("invalid");
          return;
        }
        copy.classList.remove("invalid");
      }
      setControlValue(original, copy.tagName === "SELECT" ? copy.value : readValue(copy));
      copy.classList.toggle("changed", original.classList.contains("changed"));
    };
    copy.addEventListener("change", pass);
    if (copy.tagName !== "SELECT" && copy.type !== "checkbox") copy.addEventListener("input", pass);
    return copy;
  }

  function showFound() {
    const words = findWords();
    if (!words.length) {
      findPop.hidden = true;
      return;
    }
    // The likeliest first: a name that holds the words (the shortest
    // first), then a field name, then a meaning, the one that says them
    // soonest first.
    const rank = (row) => {
      const label = row.querySelector("label");
      const name = (label?.dataset.label ?? label?.textContent ?? "").toLowerCase();
      const field = (row.querySelector("input, select")?.dataset.name ?? "").replace(/_/g, " ");
      const meaning = (row.title || "").toLowerCase().replace(/_/g, " ").indexOf(words[0]);
      const where = meaning < 0 ? Infinity : meaning;
      // Of the names that hold them, the shortest (the closest) first.
      if (words.every((word) => name.includes(word))) return [0, name.length];
      if (words.every((word) => field.includes(word))) return [1, field.length];
      return [2, where];
    };
    const rows = [...form.querySelectorAll(".field")]
      .filter((row) => !row.hidden
        && row.querySelector("input, select")
        && words.every((word) => rowText(row).includes(word)))
      .map((row) => [rank(row), row])
      .sort(([a], [b]) => a[0] - b[0] || a[1] - b[1])
      .map(([, row]) => row);
    findPop.replaceChildren();
    for (const row of rows.slice(0, FIND_LIMIT)) {
      const original = row.querySelector("select.kind") || row.querySelector("input, select");
      const item = document.createElement("div");
      item.className = "found";
      const name = document.createElement("span");
      name.className = "name";
      const label = row.querySelector("label");
      name.textContent = label?.dataset.label ?? label?.textContent ?? original.dataset.name;
      markWords(name, words);
      const control = document.createElement("span");
      control.className = "control";
      control.appendChild(proxy(original));
      const meaning = document.createElement("span");
      meaning.className = "meaning";
      meaning.textContent = (row.title || "").split("\n")[0];
      meaning.title = row.title || "";
      const links = document.createElement("span");
      links.className = "places";
      for (const place of places(row, original)) {
        const link = document.createElement("button");
        link.type = "button";
        link.textContent = place.title;
        link.addEventListener("click", () => {
          findPop.hidden = true;
          place.go();
        });
        links.appendChild(link);
      }
      item.append(name, control, meaning, links);
      findPop.appendChild(item);
    }
    const note = document.createElement("p");
    note.className = "note";
    note.textContent = rows.length === 0
      ? "No setting matches."
      : rows.length > FIND_LIMIT
        ? `${rows.length - FIND_LIMIT} more: add a word to narrow it down.`
        : "";
    if (note.textContent) findPop.appendChild(note);
    const box = findBox.getBoundingClientRect();
    findPop.style.top = `${box.bottom + 4}px`;
    findPop.style.left = `${Math.max(10, Math.min(box.right - 560, window.innerWidth - 570))}px`;
    findPop.hidden = false;
  }

  findBox.addEventListener("input", showFound);
  findBox.addEventListener("focus", showFound);
  findBox.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      if (findBox.value) findBox.value = "";
      findPop.hidden = true;
      findBox.blur();
    } else if (event.key === "Enter") {
      // The first setting found, where it is set.
      findPop.querySelector(".found .places button")?.click();
    }
  });
  document.addEventListener("pointerdown", (event) => {
    if (!findPop.hidden && !event.target.closest(".find-pop, .menubar .find")) findPop.hidden = true;
  });
  // "/" goes to the bar's search (before app.js sends it to the form's).
  document.addEventListener("keydown", (event) => {
    if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey) return;
    if (event.target.closest?.("input, select, textarea, [contenteditable]")) return;
    if (document.querySelector("dialog[open]")) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    findBox.focus();
    findBox.select();
  }, true);

  const click = (selector) => () => document.querySelector(selector)?.click();
  const enabled = (selector) => () => {
    const button = document.querySelector(selector);
    return Boolean(button) && !button.disabled;
  };
  const checked = (id) => () => byId(id).checked;
  const toggle = (id) => () => byId(id).click();
  const resultShown = () => !output.classList.contains("hidden");
  const resultTab = (id) => () => {
    showPage("result");
    showSub(id);
  };

  const MENUS = [
    ["File", () => [
      { label: "New design", run: click("#reset"), enabled: enabled("#reset") },
      { label: "Open design…", key: "O", run: click("#load-design"), enabled: enabled("#load-design") },
      ...recentItems(),
      "-",
      { label: "Save design", key: "S", run: click("#save-design"), enabled: enabled("#save-design") },
      "-",
      {
        label: "Print the result…",
        run: () => { showPage("result"); byId("print-result").click(); },
        enabled: resultShown,
      },
    ]],
    ["Edit", () => [
      { label: "Undo", key: "Z", run: click(".undo-button"), enabled: enabled(".undo-button") },
      { label: "Redo", key: "⇧Z", run: click(".redo-button"), enabled: enabled(".redo-button") },
      "-",
      {
        label: "Find a setting…",
        key: "/",
        plainKey: true,
        run: () => findBox.focus(),
      },
    ]],
    ["Design", () => PAGES.filter((page) => page.id !== "settings" && page.id !== "result").map((page) => ({
      label: page.id === "design" ? "Instrument and style" : page.title,
      run: () => showPage(page.id),
      enabled: () => available(page.id),
      ticked: () => current === page.id,
    }))],
    ["Settings", () => [
      ...groups().map((group) => ({
        label: group.dataset.title,
        run: () => { showPage("settings"); showGroup(group.dataset.title); },
        ticked: () => current === "settings" && groupTitle === group.dataset.title,
      })),
      "-",
      { label: "Show all advanced settings", run: toggle("show-advanced"), ticked: checked("show-advanced") },
      { label: "Only the settings changed", run: toggle("changed-only"), ticked: checked("changed-only") },
    ]],
    ["Build", () => [
      { label: "Build 3D and CNC files", key: "↩", run: () => buildButton.click(), enabled: () => !buildButton.disabled },
      "-",
      ...SUBS.map(([id, title]) => ({
        label: title,
        run: resultTab(id),
        enabled: resultShown,
        ticked: () => current === "result" && subButtons.get(id).classList.contains("on"),
      })),
    ]],
    ["View", () => [
      { label: "Easy mode", run: toggle("easy-mode"), ticked: checked("easy-mode") },
      { label: "Dark mode", run: () => setDark(!isDark()), ticked: isDark },
      "-",
      { label: "Classic UI", run: () => useLayout("classic") },
    ]],
    ["Help", () => [
      { label: "Tour", run: click("#start-tour") },
      { label: "Shortcuts", key: "?", plainKey: true, run: click("#show-keys") },
      "-",
      { label: "What this page does", run: () => { showPage("design"); byId("intro").scrollIntoView(); } },
      {
        label: "Source and documentation",
        run: () => window.open("https://github.com/jolappi/CNCguitarwizard", "_blank", "noopener"),
      },
    ]],
  ];

  // The designs last saved or loaded here (the classic Recent menu's).
  function recentItems() {
    const recent = byId("recent-designs");
    if (!recent || recent.hidden) return [];
    const buttons = [...recent.querySelectorAll(".menu-items button")];
    if (!buttons.length) return [];
    return [
      { label: "Recent designs", heading: true },
      ...buttons.map((button) => ({ label: `   ${button.textContent}`, run: () => button.click() })),
    ];
  }

  const pop = document.createElement("div");
  pop.className = "menu-pop";
  pop.hidden = true;
  pop.setAttribute("role", "menu");
  let openTitle = null;

  function openMenu(title, items) {
    for (const other of bar.querySelectorAll(".menu-title")) other.classList.toggle("open", other === title);
    openTitle = title;
    pop.replaceChildren();
    for (const item of items()) {
      if (item === "-") {
        pop.appendChild(document.createElement("hr"));
        continue;
      }
      if (item.heading) {
        const label = document.createElement("div");
        label.className = "menu-label";
        label.textContent = item.label;
        pop.appendChild(label);
        continue;
      }
      const button = document.createElement("button");
      button.type = "button";
      button.setAttribute("role", "menuitem");
      const name = document.createElement("span");
      const tick = document.createElement("span");
      tick.className = "tick";
      tick.textContent = item.ticked && item.ticked() ? "✓" : "";
      name.append(tick, item.label);
      button.appendChild(name);
      if (item.key) {
        const key = document.createElement("span");
        key.className = "key";
        key.textContent = item.plainKey ? item.key : `${KEY}${item.key}`;
        button.appendChild(key);
      }
      button.disabled = item.enabled ? !item.enabled() : false;
      button.addEventListener("click", () => {
        closeMenu();
        item.run();
      });
      pop.appendChild(button);
    }
    const box = title.getBoundingClientRect();
    pop.style.left = `${Math.min(box.left, window.innerWidth - 250)}px`;
    pop.style.top = `${box.bottom + 2}px`;
    pop.hidden = false;
  }

  function closeMenu() {
    pop.hidden = true;
    openTitle = null;
    for (const title of bar.querySelectorAll(".menu-title")) title.classList.remove("open");
  }

  for (const [name, items] of MENUS) {
    const title = document.createElement("button");
    title.type = "button";
    title.className = "menu-title";
    title.textContent = name;
    title.setAttribute("aria-haspopup", "menu");
    title.addEventListener("click", () => {
      if (openTitle === title) closeMenu();
      else openMenu(title, items);
    });
    // As in a desktop program: once a menu is open, the pointer over
    // another title opens that one.
    title.addEventListener("pointerenter", () => {
      if (openTitle && openTitle !== title) openMenu(title, items);
    });
    bar.appendChild(title);
  }
  const spacer = document.createElement("span");
  spacer.className = "spacer";
  bar.append(spacer, findBox, barBuild);
  document.body.prepend(bar);
  document.body.append(pop, findPop, statusBar);

  document.addEventListener("pointerdown", (event) => {
    if (openTitle && !event.target.closest(".menu-pop, .menu-title")) closeMenu();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && openTitle) closeMenu();
  });

  // A page's menu entry follows what is there (a headless neck has no
  // headstock to draw): showing one that went away goes to the instrument.
  const watch = new MutationObserver(() => {
    if (current && !available(current)) showPage("design");
  });
  for (const part of document.querySelectorAll("[data-page]")) {
    watch.observe(part, { attributes: true, attributeFilter: ["class"] });
  }

  const kept = stored(PAGE);
  showPage(kept && available(kept) ? kept : "design");
})();
