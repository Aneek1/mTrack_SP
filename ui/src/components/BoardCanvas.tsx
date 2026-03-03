import { useEffect, useMemo, useRef, useState } from "react";
import type { ClientControlMessage, ServerState } from "../types";
import { canvasToBoard, computeFitTransform, drawBoardScene } from "../render";

export function BoardCanvas(props: {
  state: ServerState | null;
  onSend: (msg: ClientControlMessage) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [size, setSize] = useState<{ w: number; h: number }>({ w: 800, h: 600 });

  const transform = useMemo(() => {
    if (!props.state) return null;
    return computeFitTransform(size.w, size.h, props.state.board.width, props.state.board.height, 18);
  }, [props.state, size]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      const r = el.getBoundingClientRect();
      setSize({ w: Math.max(10, Math.floor(r.width)), h: Math.max(10, Math.floor(r.height)) });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const state = props.state;
    const t = transform;
    if (!canvas || !state || !t) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(size.w * dpr);
    canvas.height = Math.floor(size.h * dpr);
    canvas.style.width = `${size.w}px`;
    canvas.style.height = `${size.h}px`;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, size.w, size.h);

    // background
    ctx.fillStyle = "#0b0b0e";
    ctx.fillRect(0, 0, size.w, size.h);

    drawBoardScene(ctx, state, t);
  }, [props.state, size, transform]);

  function handleClick(evt: React.MouseEvent<HTMLCanvasElement>): void {
    const state = props.state;
    const t = transform;
    if (!state || !t) return;
    const rect = (evt.target as HTMLCanvasElement).getBoundingClientRect();
    const x = evt.clientX - rect.left;
    const y = evt.clientY - rect.top;
    const [bx, by] = canvasToBoard(t, x, y);
    props.onSend({ type: "set_target", x: bx, y: by });
  }

  return (
    <div ref={containerRef} style={{ width: "100%", height: "100%", position: "relative" }}>
      <canvas
        ref={canvasRef}
        onClick={handleClick}
        style={{ width: "100%", height: "100%", borderRadius: 12, cursor: "crosshair" }}
      />
      {!props.state ? (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "grid",
            placeItems: "center",
            color: "#cfd8dc",
            fontSize: 14,
          }}
        >
          Waiting for backend state…
        </div>
      ) : null}
    </div>
  );
}

