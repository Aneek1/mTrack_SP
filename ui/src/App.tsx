import { useEffect, useMemo, useRef, useState } from "react";
import "./index.css";
import type { ClientControlMessage, ServerState } from "./types";
import { BackendWS } from "./ws";
import { BoardCanvas } from "./components/BoardCanvas";
import { SidePanel } from "./components/SidePanel";

function getWSUrl(): string {
  const fromEnv = import.meta.env.VITE_BACKEND_WS_URL as string | undefined;
  return fromEnv ?? "ws://127.0.0.1:8765/ws";
}

function App() {
  const [state, setState] = useState<ServerState | null>(null);
  const [connected, setConnected] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | undefined>(undefined);

  const wsRef = useRef<BackendWS | null>(null);

  useEffect(() => {
    const ws = new BackendWS({
      url: getWSUrl(),
      onState: (s) => setState(s),
      onStatus: (st) => {
        setConnected(st.connected);
        setStatusMsg(st.message);
      },
    });
    wsRef.current = ws;
    ws.connect();
    return () => ws.close();
  }, []);

  const send = useMemo(() => {
    return (msg: ClientControlMessage) => wsRef.current?.send(msg);
  }, []);

  // Keyboard manual velocity: WASD / arrows -> sends -1/0/1
  useEffect(() => {
    const pressed = new Set<string>();
    function recomputeAndSend(): void {
      let dx: -1 | 0 | 1 = 0;
      let dy: -1 | 0 | 1 = 0;
      if (pressed.has("ArrowLeft") || pressed.has("a")) dx = -1;
      if (pressed.has("ArrowRight") || pressed.has("d")) dx = 1;
      if (pressed.has("ArrowUp") || pressed.has("w")) dy = -1;
      if (pressed.has("ArrowDown") || pressed.has("s")) dy = 1;
      send({ type: "manual_velocity", dx, dy });
    }
    function onKeyDown(e: KeyboardEvent): void {
      if (e.repeat) return;
      const k = e.key.length === 1 ? e.key.toLowerCase() : e.key;
      if (k === " ") {
        send({ type: "toggle_mode" });
        return;
      }
      if (k === "c") send({ type: "change_profile" });
      if (k === "h") send({ type: "home" });
      pressed.add(k);
      recomputeAndSend();
    }
    function onKeyUp(e: KeyboardEvent): void {
      const k = e.key.length === 1 ? e.key.toLowerCase() : e.key;
      pressed.delete(k);
      recomputeAndSend();
    }
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
    };
  }, [send]);

  return (
    <div className="appRoot">
      <div className="topBar">
        <div className="titleBlock">
          <div className="title">mTrac Digital Twin — High-Mix Visual Inspection</div>
          <div className="subtitle">
            Perception (YOLO-ready) → Search (A*) → Hover/Dwell → PASS/FAIL → mTrac logs
          </div>
        </div>
      </div>

      <div className="contentGrid">
        <div className="boardPane">
          <BoardCanvas state={state} onSend={send} />
        </div>
        <div className="sidePane">
          <SidePanel state={state} connected={connected} statusMsg={statusMsg} onSend={send} />
        </div>
      </div>
    </div>
  );
}

export default App;
