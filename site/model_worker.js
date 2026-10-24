// The finished model in the other 3D formats, made as files here in the
// browser and off the page's thread: Pyodide with cncguitarwizard and
// OpenCascade (replicad-opencascadejs) run the build's FreeCAD script
// (backends.occt) and write each format's files into a ZIP. One worker
// holds one model (the page starts a new one for a new build): OpenCascade
// keeps what it makes, so a second model would only crowd it.
import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.mjs";

const PYODIDE_INDEX = "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/";
const OPENCASCADE = "https://cdn.jsdelivr.net/npm/replicad-opencascadejs@1.1.0/dist/";

let ready = null;

const progress = (text) => self.postMessage({ type: "progress", text });

async function start(wheel) {
  progress("Loading Python for the 3D model…");
  const pyodide = await loadPyodide({ indexURL: PYODIDE_INDEX });
  await pyodide.loadPackage("micropip");
  await pyodide.pyimport("micropip").install(wheel);
  progress("Loading OpenCascade, the CAD kernel (about 7 MB, kept by the browser)…");
  const { default: openCascade } = await import(OPENCASCADE + "replicad_single.js");
  const oc = await openCascade({ locateFile: (file) => OPENCASCADE + file });
  pyodide.globals.set("open_cascade", oc);
  pyodide.runPython("from cncguitarwizard.backends.occt import model\nmodel.connect(open_cascade)");
  pyodide.setStdout({ batched: (text) => text.trim() && progress(text.trim()) });
  return pyodide;
}

self.onmessage = async ({ data }) => {
  try {
    ready ??= start(data.wheel);
    const pyodide = await ready;
    pyodide.globals.set("model_script", data.script);
    pyodide.globals.set("model_format", data.format);
    pyodide.globals.set("model_name", data.name || "");
    const result = pyodide.runPython(
      "from cncguitarwizard.backends.occt import model\n" +
      "model.export_zip(model_script, model_format, model_name)",
    );
    const [name, bytes] = result.toJs();
    result.destroy();
    self.postMessage({ type: "done", name, bytes }, [bytes.buffer]);
  } catch (error) {
    // A Python error's message is its whole traceback (kept in the console):
    // its last line says what went wrong.
    const message = String(error.message || error).trim();
    console.error(message);
    self.postMessage({ type: "error", text: message.split("\n").at(-1) });
  }
};
