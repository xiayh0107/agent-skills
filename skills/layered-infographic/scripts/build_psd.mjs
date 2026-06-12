// Build a real multi-layer .psd from a psd_manifest.json (produced by
// split_svg_layers.py). Each layer becomes a named PSD layer; the composite
// is stored as the flattened preview so any viewer shows the image (not black).
//
// Usage: node build_psd.mjs <psd_manifest.json> [outDir]
// Requires: ag-psd, pngjs  (run `npm install` in this scripts/ dir once)
import { writePsd } from 'ag-psd';
import { PNG } from 'pngjs';
import fs from 'fs';
import path from 'path';

const manifestPath = process.argv[2];
if (!manifestPath) {
  console.error('usage: node build_psd.mjs <psd_manifest.json> [outDir]');
  process.exit(1);
}
const dir = path.dirname(path.resolve(manifestPath));
const m = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));

const load = (f) => {
  const g = PNG.sync.read(fs.readFileSync(path.join(dir, f)));
  return { width: g.width, height: g.height, data: new Uint8ClampedArray(g.data) };
};

const children = m.layers.map((L, i) => ({
  name: L.name || `layer ${i + 1}`,   // ASCII-safe names render in every tool
  imageData: load(L.file),
}));

const psd = { width: m.width, height: m.height, children };
if (m.composite) psd.imageData = load(m.composite);   // flattened preview (avoids black)

const outDir = process.argv[3] || dir;
const out = path.join(outDir, m.out || 'output.psd');
fs.writeFileSync(out, Buffer.from(writePsd(psd)));
console.log(`PSD written: ${out}  (${children.length} layers: ${children.map(c => c.name).join(', ')})`);
