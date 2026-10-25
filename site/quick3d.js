// The quick 3D model's viewer (three.js): the parts webapp.quick_model
// makes, turned with the mouse or a finger (drag to turn, wheel or pinch
// to zoom toward the pointer, right-drag or two fingers to move), lit from
// above. Smooth but
// for its edges (creased normals past 35 degrees), so a roundover reads
// round and an edge sharp. The first model drawn is framed; later ones
// keep the view, so a change is seen from where it was looked at.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { toCreasedNormals } from "three/addons/utils/BufferGeometryUtils.js";

export function createViewer(holder) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  holder.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xf4efe4);
  // Z up: the guitar lies face up, its neck along X.
  const camera = new THREE.PerspectiveCamera(35, 1, 1, 20000);
  camera.up.set(0, 0, 1);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x8a7a66, 1.6));
  const sun = new THREE.DirectionalLight(0xffffff, 1.6);
  sun.position.set(-300, -500, 900);
  scene.add(sun);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = false;
  // Zoomed toward the pointer, so a detail (a fret, a tuner) is zoomed to.
  controls.zoomToCursor = true;
  const group = new THREE.Group();
  scene.add(group);
  let parts = [];
  let framed = false;

  const render = () => renderer.render(scene, camera);
  controls.addEventListener("change", render);

  function resize() {
    const width = holder.clientWidth || 1;
    const height = holder.clientHeight || 1;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    render();
  }
  new ResizeObserver(resize).observe(holder);

  function frame() {
    const box = new THREE.Box3().setFromObject(group);
    if (box.isEmpty()) return;
    const centre = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3()).length();
    controls.target.copy(centre);
    // The whole guitar (its bounding sphere) inside the narrower of the
    // view's two angles, seen from in front of the body, above and to the
    // treble side.
    const vertical = THREE.MathUtils.degToRad(camera.fov);
    const horizontal = 2 * Math.atan(Math.tan(vertical / 2) * camera.aspect);
    const distance = (size / 2) / Math.sin(Math.min(vertical, horizontal) / 2);
    const toward = new THREE.Vector3(0.55, -0.75, 0.6).normalize().multiplyScalar(distance);
    camera.position.copy(centre).add(toward);
    camera.near = size / 200;
    camera.far = size * 20;
    camera.updateProjectionMatrix();
    controls.update();
    render();
  }

  function show(newParts) {
    for (const mesh of [...group.children]) {
      group.remove(mesh);
      mesh.geometry.dispose();
      mesh.material.dispose();
    }
    parts = newParts;
    for (const part of parts) {
      let geometry = new THREE.BufferGeometry();
      geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(part.positions), 3));
      geometry.setIndex(new THREE.BufferAttribute(new Uint32Array(part.triangles), 1));
      geometry = toCreasedNormals(geometry, (35 * Math.PI) / 180);
      const material = new THREE.MeshStandardMaterial({
        color: new THREE.Color(part.colour), roughness: 0.75, metalness: 0.0,
      });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.name = part.name;
      group.add(mesh);
    }
    if (!framed) {
      framed = true;
      resize();
      frame();
    } else {
      render();
    }
  }

  // The parts as one binary STL, in millimetres.
  function stl() {
    let count = 0;
    for (const part of parts) count += new Uint32Array(part.triangles).length / 3;
    const out = new DataView(new ArrayBuffer(84 + 50 * count));
    const label = "cncguitarwizard quick model";
    for (let index = 0; index < label.length; index += 1) out.setUint8(index, label.charCodeAt(index));
    out.setUint32(80, count, true);
    let at = 84;
    for (const part of parts) {
      const p = new Float32Array(part.positions);
      const t = new Uint32Array(part.triangles);
      for (let index = 0; index < t.length; index += 3) {
        const [a, b, c] = [t[index], t[index + 1], t[index + 2]].map((v) => [p[3 * v], p[3 * v + 1], p[3 * v + 2]]);
        const u = [b[0] - a[0], b[1] - a[1], b[2] - a[2]];
        const v = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
        const n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]];
        const length = Math.hypot(...n) || 1;
        for (const value of [...n.map((x) => x / length), ...a, ...b, ...c]) {
          out.setFloat32(at, value, true);
          at += 4;
        }
        at += 2;
      }
    }
    return out.buffer;
  }

  return { show, stl, frame };
}
