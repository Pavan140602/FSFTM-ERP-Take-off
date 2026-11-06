// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
/**
 * Dynamic Fill (Bluebeam-style): click inside a bounded region on the PDF
 * and flood-fill it to measure the enclosed area.
 *
 * Pipeline:
 *  1. Render the PDF page to an offscreen canvas at a fixed scale.
 *  2. Flood-fill from the click point (color similarity tolerance).
 *  3. Trace the filled region's boundary via marching squares.
 *  4. Simplify with Douglas-Peucker, map back to PDF coordinates.
 */

export interface Point {
  x: number;
  y: number;
}

/** Color similarity tolerance (0-255 per channel sum). */
const FILL_TOLERANCE = 48;
/** Max pixels to fill (safety cap). */
const MAX_FILL_PIXELS = 2_000_000;

function colorDist(
  data: Uint8ClampedArray,
  i1: number,
  i2: number,
): number {
  return (
    Math.abs(data[i1] - data[i2]) +
    Math.abs(data[i1 + 1] - data[i2 + 1]) +
    Math.abs(data[i1 + 2] - data[i2 + 2])
  );
}

/**
 * Flood fill from (sx, sy). Returns a bitmask (1 = filled) or null if the
 * region is too large / unbounded.
 */
export function floodFill(
  imageData: ImageData,
  sx: number,
  sy: number,
): Uint8Array | null {
  const { width, height, data } = imageData;
  if (sx < 0 || sx >= width || sy < 0 || sy >= height) return null;

  const mask = new Uint8Array(width * height);
  const seedIdx = (sy * width + sx) * 4;
  const stack: number[] = [sy * width + sx];
  mask[sy * width + sx] = 1;
  let filled = 0;

  while (stack.length > 0) {
    const idx = stack.pop()!;
    filled++;
    if (filled > MAX_FILL_PIXELS) return null; // Unbounded — bail out

    const x = idx % width;
    const y = Math.floor(idx / width);
    const cur = idx * 4;

    // 4-neighbors
    const neighbors: number[] = [];
    if (x > 0) neighbors.push(idx - 1);
    if (x < width - 1) neighbors.push(idx + 1);
    if (y > 0) neighbors.push(idx - width);
    if (y < height - 1) neighbors.push(idx + width);

    for (const nIdx of neighbors) {
      if (mask[nIdx]) continue;
      const n = nIdx * 4;
      if (colorDist(data, seedIdx, n) <= FILL_TOLERANCE) {
        mask[nIdx] = 1;
        stack.push(nIdx);
      }
    }
  }
  return mask;
}

/**
 * Trace the boundary of a filled region using marching squares.
 * Returns the outline as pixel coordinates.
 */
export function traceBoundary(mask: Uint8Array, width: number, height: number): Point[] {
  // Find a starting edge pixel (filled pixel with unfilled neighbor)
  let startX = -1;
  let startY = -1;
  outer: for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      if (mask[y * width + x]) {
        // Check if it's on the boundary
        if (
          x === 0 || x === width - 1 || y === 0 || y === height - 1 ||
          !mask[y * width + x - 1] || !mask[y * width + x + 1] ||
          !mask[(y - 1) * width + x] || !mask[(y + 1) * width + x]
        ) {
          startX = x;
          startY = y;
          break outer;
        }
      }
    }
  }
  if (startX === -1) return [];

  // Moore neighbor tracing (clockwise)
  const boundary: Point[] = [];
  const dirs = [
    [1, 0], [1, 1], [0, 1], [-1, 1],
    [-1, 0], [-1, -1], [0, -1], [1, -1],
  ];
  let cx = startX;
  let cy = startY;
  let dir = 0;
  const maxSteps = width * height;
  let steps = 0;

  do {
    boundary.push({ x: cx, y: cy });
    // Find next boundary pixel clockwise from dir
    let found = false;
    for (let i = 0; i < 8; i++) {
      const nd = (dir + i) % 8;
      const nx = cx + dirs[nd]![0];
      const ny = cy + dirs[nd]![1];
      if (nx >= 0 && nx < width && ny >= 0 && ny < height && mask[ny * width + nx]) {
        cx = nx;
        cy = ny;
        dir = (nd + 5) % 8; // Turn to continue clockwise
        found = true;
        break;
      }
    }
    if (!found) break;
    steps++;
    if (steps > maxSteps) break;
  } while (cx !== startX || cy !== startY);

  return boundary;
}

/** Douglas-Peucker polygon simplification. */
export function simplifyPolygon(points: Point[], epsilon: number): Point[] {
  if (points.length <= 2) return points;

  const keep = new Array(points.length).fill(false);
  keep[0] = true;
  keep[points.length - 1] = true;

  const stack: [number, number][] = [[0, points.length - 1]];
  while (stack.length > 0) {
    const [s, e] = stack.pop()!;
    let maxDist = 0;
    let maxIdx = -1;
    const a = points[s]!;
    const b = points[e]!;
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const len2 = dx * dx + dy * dy;
    for (let i = s + 1; i < e; i++) {
      const p = points[i]!;
      let d: number;
      if (len2 < 1e-12) {
        d = Math.hypot(p.x - a.x, p.y - a.y);
      } else {
        const t = Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / len2));
        d = Math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy));
      }
      if (d > maxDist) {
        maxDist = d;
        maxIdx = i;
      }
    }
    if (maxDist > epsilon && maxIdx !== -1) {
      keep[maxIdx] = true;
      stack.push([s, maxIdx], [maxIdx, e]);
    }
  }
  return points.filter((_, i) => keep[i]);
}

/**
 * Full pipeline: given a rendered page canvas and a click in PDF-top-left
 * coords, return the filled region boundary in PDF-top-left coords.
 *
 * `renderScale` = canvas pixels per PDF unit. `pageHeightPdf` for Y-flip.
 */
export function dynamicFill(
  pageCanvas: HTMLCanvasElement,
  clickPdf: Point,
  renderScale: number,
): Point[] | null {
  const ctx = pageCanvas.getContext('2d', { willReadFrequently: true });
  if (!ctx) return null;
  const { width, height } = pageCanvas;
  const imageData = ctx.getImageData(0, 0, width, height);

  // Map PDF coords to canvas pixels
  const sx = Math.floor(clickPdf.x * renderScale);
  const sy = Math.floor(clickPdf.y * renderScale);

  const mask = floodFill(imageData, sx, sy);
  if (!mask) return null;

  const boundary = traceBoundary(mask, width, height);
  if (boundary.length < 3) return null;

  // Simplify (epsilon in pixels)
  const simplified = simplifyPolygon(boundary, 2.0);
  if (simplified.length < 3) return null;

  // Map back to PDF coords
  return simplified.map((p) => ({
    x: p.x / renderScale,
    y: p.y / renderScale,
  }));
}
