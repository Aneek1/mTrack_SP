import { useEffect, useMemo, useRef, useState } from "react";
import type { ClientControlMessage, ServerState } from "../types";
import { drawCameraPatch } from "../render";

// Test case generation state
interface TestCaseState {
  testId: string | null;
  isLoading: boolean;
  lastResult: any;
  sessionActive: boolean;
}

function Pill(props: { text: string; tone?: "ok" | "warn" | "bad" | "neutral" }) {
  const tone = props.tone ?? "neutral";
  const bg =
    tone === "ok" ? "#123a22" : tone === "warn" ? "#3a2d12" : tone === "bad" ? "#3a1212" : "#1a1a22";
  const fg =
    tone === "ok" ? "#63ff9a" : tone === "warn" ? "#ffd24a" : tone === "bad" ? "#ff6b6b" : "#cfd8dc";
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        borderRadius: 999,
        background: bg,
        color: fg,
        border: "1px solid #2a2a35",
        fontSize: 12,
        whiteSpace: "nowrap",
      }}
    >
      {props.text}
    </span>
  );
}

export function SidePanel(props: {
  state: ServerState | null;
  connected: boolean;
  statusMsg?: string;
  onSend: (msg: ClientControlMessage) => void;
}) {
  const camRef = useRef<HTMLCanvasElement | null>(null);
  const [camSize] = useState({ w: 320, h: 200 });

  // Test case state
  const [testCaseState, setTestCaseState] = useState<TestCaseState>({
    testId: null,
    isLoading: false,
    lastResult: null,
    sessionActive: false
  });

  // Calculate defect statistics
  const defectStats = useMemo(() => {
    if (!props.state) return { total: 0, passed: 0, failed: 0, passRate: 0 };

    const results = props.state.inspection_results;
    const total = Object.keys(results).length;
    const passed = Object.values(results).filter(r => r === "PASS").length;
    const failed = total - passed;
    const passRate = total > 0 ? (passed / total) * 100 : 0;

    return { total, passed, failed, passRate };
  }, [props.state]);

  useEffect(() => {
    const canvas = camRef.current;
    const s = props.state;
    if (!canvas || !s) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(camSize.w * dpr);
    canvas.height = Math.floor(camSize.h * dpr);
    canvas.style.width = `${camSize.w}px`;
    canvas.style.height = `${camSize.h}px`;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    drawCameraPatch(ctx, s, camSize.w, camSize.h);
  }, [props.state, camSize.h, camSize.w]);

  // Test case management functions
  const loadTestCaseInternal = (data: any) => {
    setTestCaseState(prev => ({ ...prev, isLoading: true }));
    props.onSend({ type: "load_test_case", test_case_data: data });

    // Poll for result
    const checkResult = setInterval(() => {
      fetch("/load_result")
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            setTestCaseState(prev => ({
              ...prev,
              isLoading: false,
              sessionActive: true
            }));
            clearInterval(checkResult);
          }
        })
        .catch(() => clearInterval(checkResult));
    }, 500);
  };

  const generateTestCase = () => {
    setTestCaseState(prev => ({ ...prev, isLoading: true }));
    props.onSend({
      type: "generate_test_case",
      defect_rate: 0.15,
      difficulty_level: "medium",
      num_components: 20
    });

    // Poll for result
    const checkResult = setInterval(() => {
      fetch("/test_case_result")
        .then(res => res.json())
        .then(data => {
          if (data.test_id) {
            setTestCaseState(prev => ({
              ...prev,
              isLoading: false,
              lastResult: data,
              testId: data.test_id
            }));
            clearInterval(checkResult);

            // Automatically load the newly generated test case
            loadTestCaseInternal(data);
          }
        })
        .catch(() => clearInterval(checkResult));
    }, 500);
  };

  const loadTestCase = () => {
    if (!testCaseState.lastResult) return;
    loadTestCaseInternal(testCaseState.lastResult);
  };

  const endSession = () => {
    props.onSend({ type: "end_test_session" });

    // Poll for result
    const checkResult = setInterval(() => {
      fetch("/session_result")
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            setTestCaseState(prev => ({
              ...prev,
              sessionActive: false,
              lastResult: { ...prev.lastResult, sessionMetrics: data.session_metrics }
            }));
            clearInterval(checkResult);
          }
        })
        .catch(() => clearInterval(checkResult));
    }, 500);
  };

  const s = props.state;
  const mode = s?.body.mode ?? "AI";
  const aiTone = mode === "SAFE_RETURN" ? "bad" : mode === "MANUAL" ? "warn" : "ok";

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        gap: 12,
        padding: 12,
        background: "#0f0f14",
        border: "1px solid #232331",
        borderRadius: 12,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <Pill text={props.connected ? "Connected" : "Disconnected"} tone={props.connected ? "ok" : "bad"} />
            <Pill text={`Mode: ${mode}`} tone={aiTone} />
          </div>
          <div style={{ color: "#cfd8dc", fontSize: 12, opacity: 0.9 }}>
            {props.statusMsg ?? (props.connected ? "Streaming state…" : "Start backend then connect.")}
          </div>
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={() => props.onSend({ type: "toggle_mode" })}>Toggle AI/MANUAL</button>
          <button onClick={() => props.onSend({ type: "change_profile" })}>High-Mix</button>
          <button onClick={() => props.onSend({ type: "home" })}>Home</button>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <div style={{ color: "#e6e6ef", fontSize: 13, fontWeight: 600 }}>Inspection Results</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ color: "#cfd8dc", fontSize: 12 }}>Total Inspected:</span>
            <Pill text={`${defectStats.total}`} tone="neutral" />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ color: "#cfd8dc", fontSize: 12 }}>Passed:</span>
            <Pill text={`${defectStats.passed}`} tone="ok" />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ color: "#cfd8dc", fontSize: 12 }}>Failed:</span>
            <Pill text={`${defectStats.failed}`} tone={defectStats.failed > 0 ? "bad" : "ok"} />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ color: "#cfd8dc", fontSize: 12 }}>Pass Rate:</span>
            <Pill text={`${defectStats.passRate.toFixed(1)}%`} tone={defectStats.passRate >= 95 ? "ok" : defectStats.passRate >= 80 ? "warn" : "bad"} />
          </div>
          {defectStats.failed > 0 && (
            <div style={{
              padding: "8px 12px",
              background: "#3a1212",
              border: "1px solid #ff4d4d",
              borderRadius: 8,
              marginTop: 4
            }}>
              <div style={{ color: "#ff6b6b", fontSize: 12, fontWeight: 600 }}>
                ⚠️ {defectStats.failed} defect{defectStats.failed > 1 ? 's' : ''} detected
              </div>
            </div>
          )}
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <div style={{ color: "#e6e6ef", fontSize: 13, fontWeight: 600 }}>Digital Twin Test Cases</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button
              onClick={generateTestCase}
              disabled={testCaseState.isLoading}
              style={{
                opacity: testCaseState.isLoading ? 0.6 : 1,
                cursor: testCaseState.isLoading ? "not-allowed" : "pointer"
              }}
            >
              {testCaseState.isLoading ? "Generating..." : "Generate Test Case"}
            </button>
            <button
              onClick={loadTestCase}
              disabled={!testCaseState.lastResult || testCaseState.isLoading}
              style={{
                opacity: !testCaseState.lastResult || testCaseState.isLoading ? 0.6 : 1,
                cursor: !testCaseState.lastResult || testCaseState.isLoading ? "not-allowed" : "pointer"
              }}
            >
              Load Test Case
            </button>
            <button
              onClick={endSession}
              disabled={!testCaseState.sessionActive}
              style={{
                opacity: !testCaseState.sessionActive ? 0.6 : 1,
                cursor: !testCaseState.sessionActive ? "not-allowed" : "pointer"
              }}
            >
              End Session
            </button>
          </div>

          {testCaseState.lastResult && (
            <div style={{
              padding: "8px 12px",
              background: "#1a2a1a",
              border: "1px solid #2a4a2a",
              borderRadius: 8,
              fontSize: 11,
              color: "#cfd8dc"
            }}>
              <div><strong>Test ID:</strong> {testCaseState.lastResult.test_id}</div>
              <div><strong>Components:</strong> {testCaseState.lastResult.num_components}</div>
              <div><strong>Defects:</strong> {testCaseState.lastResult.num_defects}</div>
              <div><strong>Difficulty:</strong> {testCaseState.lastResult.difficulty_level}</div>
              {testCaseState.lastResult.sessionMetrics && (
                <>
                  <div><strong>Detection Rate:</strong> {(testCaseState.lastResult.sessionMetrics.defect_detection_rate * 100).toFixed(1)}%</div>
                  <div><strong>Avg Time:</strong> {testCaseState.lastResult.sessionMetrics.average_inspection_time.toFixed(2)}s</div>
                </>
              )}
            </div>
          )}

          {testCaseState.sessionActive && (
            <div style={{
              padding: "6px 12px",
              background: "#1a1a2a",
              border: "1px solid #4a4a6a",
              borderRadius: 8
            }}>
              <div style={{ color: "#7aa7ff", fontSize: 12, fontWeight: 600 }}>
                🔬 Session Active - AI Inspecting...
              </div>
            </div>
          )}
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <div style={{ color: "#e6e6ef", fontSize: 13, fontWeight: 600 }}>Perception: Camera FOV</div>
        <canvas ref={camRef} style={{ borderRadius: 10, border: "1px solid #2a2a35" }} />
      </div>

      <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", gap: 8 }}>
        <div style={{ color: "#e6e6ef", fontSize: 13, fontWeight: 600 }}>Thought Log</div>
        <div
          style={{
            flex: 1,
            minHeight: 0,
            overflow: "auto",
            background: "#0b0b0e",
            border: "1px solid #232331",
            borderRadius: 10,
            padding: 10,
            fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
            fontSize: 12,
            lineHeight: 1.5,
            color: "#cfd8dc",
            whiteSpace: "pre-wrap",
          }}
        >
          {(s?.thought_log_lines ?? ["(no data)"]).join("\n")}
        </div>
      </div>

      <details style={{ borderTop: "1px solid #232331", paddingTop: 10 }}>
        <summary style={{ color: "#e6e6ef", cursor: "pointer", fontWeight: 600 }}>Prompt / JSON trace</summary>
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ color: "#cfd8dc", fontSize: 12 }}>
            {s?.ai_trace ? `System: ${s.ai_trace.system_first_line}` : "No trace yet."}
          </div>
          {s?.ai_trace ? (
            <>
              <div style={{ color: "#cfd8dc", fontSize: 12 }}>
                Schema keys: {s.ai_trace.schema_keys.join(", ")}
              </div>
              <div style={{ color: "#cfd8dc", fontSize: 12 }}>{s.ai_trace.observation_summary}</div>
              <pre
                style={{
                  margin: 0,
                  padding: 10,
                  background: "#0b0b0e",
                  border: "1px solid #232331",
                  borderRadius: 10,
                  color: "#cfd8dc",
                  overflow: "auto",
                  maxHeight: 160,
                }}
              >
                {s.ai_trace.raw_json}
              </pre>
            </>
          ) : null}
        </div>
      </details>

      <details style={{ borderTop: "1px solid #232331", paddingTop: 10 }}>
        <summary style={{ color: "#e6e6ef", cursor: "pointer", fontWeight: 600 }}>YOLO (optional)</summary>
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ color: "#cfd8dc", fontSize: 12 }}>
            Backend supports switching perception via <code>set_yolo_weights</code>. If ultralytics isn’t installed,
            it will fall back to ground truth.
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={() => props.onSend({ type: "set_yolo_weights", weights_path: null })}>
              Use ground truth
            </button>
            <button
              onClick={() => {
                const p = window.prompt("Path to YOLO weights on this machine (e.g. /path/to/best.pt):");
                if (!p) return;
                props.onSend({ type: "set_yolo_weights", weights_path: p });
              }}
            >
              Set YOLO weights…
            </button>
          </div>
        </div>
      </details>
    </div>
  );
}

