import type { Detection, ServerState } from "./types";

export interface ViewTransform {
  scale: number;
  offsetX: number;
  offsetY: number;
}

export function computeFitTransform(
  canvasW: number,
  canvasH: number,
  boardW: number,
  boardH: number,
  padding: number,
): ViewTransform {
  const availW = Math.max(1, canvasW - padding * 2);
  const availH = Math.max(1, canvasH - padding * 2);
  const scale = Math.min(availW / boardW, availH / boardH);
  const drawW = boardW * scale;
  const drawH = boardH * scale;
  const offsetX = Math.floor((canvasW - drawW) / 2);
  const offsetY = Math.floor((canvasH - drawH) / 2);
  return { scale, offsetX, offsetY };
}

export function boardToCanvas(t: ViewTransform, x: number, y: number): [number, number] {
  return [t.offsetX + x * t.scale, t.offsetY + y * t.scale];
}

export function canvasToBoard(t: ViewTransform, x: number, y: number): [number, number] {
  return [(x - t.offsetX) / t.scale, (y - t.offsetY) / t.scale];
}

export function drawBoardScene(
  ctx: CanvasRenderingContext2D,
  state: ServerState,
  t: ViewTransform,
): void {
  const boardW = state.board.width;
  const boardH = state.board.height;

  // Board background
  const [x0, y0] = boardToCanvas(t, 0, 0);
  ctx.fillStyle = "#0d3b13";
  ctx.fillRect(x0, y0, boardW * t.scale, boardH * t.scale);
  ctx.strokeStyle = "#1aff6a";
  ctx.lineWidth = 2;
  ctx.strokeRect(x0, y0, boardW * t.scale, boardH * t.scale);

  // Components
  for (const c of state.components) {
    const [cx, cy] = boardToCanvas(t, c.rect.x, c.rect.y);
    ctx.fillStyle = "#bdbdbd";
    ctx.fillRect(cx, cy, c.rect.w * t.scale, c.rect.h * t.scale);

    const res = state.inspection_results[c.component_id];
    if (res) {
      if (res === "PASS") {
        ctx.strokeStyle = "#3dff7c";
        ctx.lineWidth = 3;
        ctx.setLineDash([]);
      } else {
        // Make defects more prominent with red border and dashed pattern
        ctx.strokeStyle = "#ff4d4d";
        ctx.lineWidth = 4;
        ctx.setLineDash([8, 4]);
        
        // Add defect indicator badge
        ctx.fillStyle = "#ff4d4d";
        ctx.font = "bold 14px system-ui, -apple-system, Segoe UI, Roboto, sans-serif";
        ctx.fillText("⚠", cx + c.rect.w * t.scale - 10, cy + 15);
      }
      ctx.strokeRect(cx, cy, c.rect.w * t.scale, c.rect.h * t.scale);
      ctx.setLineDash([]);
    }
  }

  // Planned path
  if (state.planned_path.length > 1) {
    ctx.strokeStyle = "#7aa7ff";
    ctx.lineWidth = 2;
    ctx.beginPath();
    state.planned_path.forEach(([px, py], idx) => {
      const [sx, sy] = boardToCanvas(t, px, py);
      if (idx === 0) ctx.moveTo(sx, sy);
      else ctx.lineTo(sx, sy);
    });
    ctx.stroke();
  }

  // Detections
  for (const d of state.detections) {
    drawDetection(ctx, d, t);
  }

  // FOV rectangle
  const [fx, fy] = state.board.fov.origin;
  const [fw, fh] = state.board.fov.size;
  const [sx, sy] = boardToCanvas(t, fx, fy);
  ctx.strokeStyle = "#ffffff55";
  ctx.lineWidth = 2;
  ctx.strokeRect(sx, sy, fw * t.scale, fh * t.scale);

  // Gantry
  const gx = state.body.x;
  const gy = state.body.y;
  const gantrySize = 40;
  const [gsx, gsy] = boardToCanvas(t, gx - gantrySize / 2, gy - gantrySize / 2);
  ctx.strokeStyle = "#4fa3ff";
  ctx.lineWidth = 2;
  ctx.strokeRect(gsx, gsy, gantrySize * t.scale, gantrySize * t.scale);
}

function drawDetection(ctx: CanvasRenderingContext2D, d: Detection, t: ViewTransform): void {
  const [x1, y1, x2, y2] = d.bbox_xyxy;
  const [sx1, sy1] = boardToCanvas(t, x1, y1);
  const [sx2, sy2] = boardToCanvas(t, x2, y2);
  const w = sx2 - sx1;
  const h = sy2 - sy1;
  const color = d.source === "yolo" ? "#ffd24a" : "#3dd3ff";
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.strokeRect(sx1, sy1, w, h);

  const label = `${d.component_id ?? d.label}:${d.label} ${d.confidence.toFixed(2)}`;
  ctx.fillStyle = color;
  ctx.font = "12px system-ui, -apple-system, Segoe UI, Roboto, sans-serif";
  ctx.fillText(label, sx1, Math.max(12, sy1 - 4));
}

export function drawCameraPatch(
  ctx: CanvasRenderingContext2D,
  state: ServerState,
  canvasW: number,
  canvasH: number,
): void {
  const [fx, fy] = state.board.fov.origin;
  const [fw, fh] = state.board.fov.size;

  // Render a small local scene in FOV coordinates (0..fw, 0..fh)
  ctx.clearRect(0, 0, canvasW, canvasH);
  const t = computeFitTransform(canvasW, canvasH, fw, fh, 0);

  // Background
  const [x0, y0] = boardToCanvas(t, 0, 0);
  ctx.fillStyle = "#0d3b13";
  ctx.fillRect(x0, y0, fw * t.scale, fh * t.scale);
  ctx.strokeStyle = "#cfd8dc";
  ctx.lineWidth = 1;
  ctx.strokeRect(x0, y0, fw * t.scale, fh * t.scale);

  // Components clipped to FOV
  for (const c of state.components) {
    const rx = c.rect.x - fx;
    const ry = c.rect.y - fy;
    if (rx + c.rect.w < 0 || ry + c.rect.h < 0 || rx > fw || ry > fh) continue;
    const [cx, cy] = boardToCanvas(t, rx, ry);
    ctx.fillStyle = "#bdbdbd";
    ctx.fillRect(cx, cy, c.rect.w * t.scale, c.rect.h * t.scale);
  }

  // Detections inside FOV
  for (const d of state.detections) {
    const [x1, y1, x2, y2] = d.bbox_xyxy;
    const dx1 = x1 - fx;
    const dy1 = y1 - fy;
    const dx2 = x2 - fx;
    const dy2 = y2 - fy;
    const [sx1, sy1] = boardToCanvas(t, dx1, dy1);
    const [sx2, sy2] = boardToCanvas(t, dx2, dy2);
    const color = d.source === "yolo" ? "#ffd24a" : "#3dd3ff";
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.strokeRect(sx1, sy1, sx2 - sx1, sy2 - sy1);
  }

  // Gantry inside FOV
  const gantrySize = 40;
  const gx = state.body.x - fx;
  const gy = state.body.y - fy;
  const [gsx, gsy] = boardToCanvas(t, gx - gantrySize / 2, gy - gantrySize / 2);
  ctx.strokeStyle = "#4fa3ff";
  ctx.lineWidth = 2;
  ctx.strokeRect(gsx, gsy, gantrySize * t.scale, gantrySize * t.scale);
}

