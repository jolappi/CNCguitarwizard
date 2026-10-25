// The quick 3D model (webapp.quick_model), made off the page's thread so
// the page keeps answering while it is: Pyodide with cncguitarwizard only,
// no CAD kernel. Each message is a design ({prototype}) and the detail set
// to add ("" for none); the answer is its parts' meshes as buffers handed
// over to the page (not copied).
import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.mjs";

const PYODIDE_INDEX = "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/";

let ready = null;

async function start(wheel) {
  const pyodide = await loadPyodide({ indexURL: PYODIDE_INDEX });
  await pyodide.loadPackage("micropip");
  await pyodide.pyimport("micropip").install(wheel);
  pyodide.runPython("from cncguitarwizard.webapp import quick_model");
  return pyodide;
}

function buffer(text) {
  const bytes = atob(text);
  const out = new Uint8Array(bytes.length);
  for (let index = 0; index < bytes.length; index += 1) out[index] = bytes.charCodeAt(index);
  return out.buffer;
}

self.onmessage = async ({ data }) => {
  try {
    ready ??= start(data.wheel);
    const pyodide = await ready;
    pyodide.globals.set("quick_payload_json", JSON.stringify(data.payload));
    pyodide.globals.set("quick_detail", data.detail || "");
    const result = JSON.parse(pyodide.runPython(
      "import json\njson.dumps(quick_model(json.loads(quick_payload_json), quick_detail))",
    ));
    if (result.error) {
      self.postMessage({ type: "error", id: data.id, text: result.error });
      return;
    }
    const parts = result.parts.map((part) => ({
      name: part.name,
      colour: part.colour,
      positions: buffer(part.positions),
      triangles: buffer(part.triangles),
    }));
    self.postMessage(
      { type: "done", id: data.id, parts },
      parts.flatMap((part) => [part.positions, part.triangles]),
    );
  } catch (error) {
    self.postMessage({ type: "error", id: data.id, text: String(error.message || error) });
  }
};
